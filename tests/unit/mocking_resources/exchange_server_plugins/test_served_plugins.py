"""
End-to-end tests for the mock server plugins of aevo, bitget, bitmart, btc_markets,
dexalot and pacifica.

Each plugin is mounted on a MockedExchangeServer and driven with the requests its real
adapter builds; the adapter must parse what the plugin serves.
"""

import asyncio
from dataclasses import dataclass

import pytest

from candles_feed.adapters.bitget.constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    SPOT_CANDLES_ENDPOINT,
)
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.factory import create_mock_server
from candles_feed.mocking_resources.core.server import MockedExchangeServer
from candles_feed.mocking_resources.core.url_patcher import ExchangeURLPatcher
from candles_feed.mocking_resources.exchange_server_plugins import (
    AevoPerpetualPlugin,
    BitgetPerpetualPlugin,
    BitgetSpotPlugin,
    BitmartPerpetualPlugin,
    BTCMarketsSpotPlugin,
    DexalotSpotPlugin,
    PacificaPerpetualPlugin,
)


@dataclass(frozen=True)
class Case:
    plugin_cls: type[ExchangePlugin]
    exchange_type: ExchangeType
    pair: str
    interval: str
    rest_path: str
    has_ws: bool = True
    route: str | None = None  # registered route pattern when it differs from rest_path


CASES = [
    Case(AevoPerpetualPlugin, ExchangeType.AEVO_PERPETUAL, "ETH-USDC", "1m", "/mark-history"),
    Case(BitgetSpotPlugin, ExchangeType.BITGET_SPOT, "BTC-USDT", "1m", SPOT_CANDLES_ENDPOINT),
    Case(
        BitgetPerpetualPlugin,
        ExchangeType.BITGET_PERPETUAL,
        "BTC-USDT",
        "1m",
        PERPETUAL_CANDLES_ENDPOINT,
    ),
    Case(
        BitmartPerpetualPlugin,
        ExchangeType.BITMART_PERPETUAL,
        "BTC-USDT",
        "1m",
        "/contract/public/kline",
    ),
    Case(
        BTCMarketsSpotPlugin,
        ExchangeType.BTC_MARKETS_SPOT,
        "BTC-AUD",
        "1m",
        "/v3/markets/BTC-AUD/candles",
        has_ws=False,
        route="/v3/markets/{market_id}/candles",
    ),
    Case(DexalotSpotPlugin, ExchangeType.DEXALOT_SPOT, "ALOT-USDC", "5m", "/trading/candlechart"),
    Case(PacificaPerpetualPlugin, ExchangeType.PACIFICA_PERPETUAL, "BTC-USDC", "1m", "/kline"),
]
WS_CASES = [c for c in CASES if c.has_ws]
IDS = [c.exchange_type.value for c in CASES]
WS_IDS = [c.exchange_type.value for c in WS_CASES]


@pytest.fixture
def make_server():
    def _make(case: Case) -> MockedExchangeServer:
        server = MockedExchangeServer(case.plugin_cls())
        server.add_trading_pair(case.pair, case.interval, 1000.0)
        return server

    return _make


def unsubscribe_variant(payload: dict) -> dict:
    """Turn a subscribe payload into the matching unsubscribe payload."""
    verb_field = next(k for k in ("op", "action", "method", "type") if k in payload)
    verb = "chart-v2-unsubscribe" if verb_field == "type" else "unsubscribe"
    return {**payload, verb_field: verb}


@pytest.mark.parametrize("case", CASES, ids=IDS)
class TestPluginContract:
    def test_is_exchange_plugin_bound_to_its_adapter(self, case):
        plugin = case.plugin_cls()
        assert isinstance(plugin, ExchangePlugin)
        assert plugin.exchange_type is case.exchange_type
        assert plugin.adapter_class is ExchangeRegistry.get_adapter_class(case.exchange_type.value)

    def test_every_route_has_a_handler(self, case):
        plugin = case.plugin_cls()
        for _path, (method, handler) in plugin.rest_routes.items():
            assert method == "GET"
            assert callable(getattr(plugin, handler))
        for handler in plugin.ws_routes.values():
            assert callable(getattr(plugin, handler))

    def test_serves_the_adapter_candle_endpoint(self, case):
        plugin = case.plugin_cls()
        assert (case.route or case.rest_path) in plugin.rest_routes
        assert plugin.rest_url.startswith("https://")

    def test_factory_resolves_plugin(self, case):
        server = create_mock_server(case.exchange_type, trading_pairs=[(case.pair, "1m", 100.0)])
        assert isinstance(server.plugin, case.plugin_cls)

    def test_url_patcher_has_mapping(self, case):
        module, attrs = ExchangeURLPatcher(
            case.exchange_type, "127.0.0.1", 1
        )._get_adapter_constants_module()
        assert module.startswith("candles_feed.adapters.")
        assert attrs["rest"].endswith("REST_URL")

    def test_interval_to_seconds(self, case):
        plugin = case.plugin_cls()
        assert plugin._interval_to_seconds("5m") == 300
        assert plugin._interval_to_seconds("1d") == 86400
        with pytest.raises(ValueError, match="Unknown interval unit"):
            plugin._interval_to_seconds("5x")


@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_rest_candles_roundtrip_through_adapter(case, make_server, aiohttp_client):
    server = make_server(case)
    client = await aiohttp_client(server.app)
    adapter = case.plugin_cls().adapter_class()

    params = adapter._get_rest_params(case.pair, case.interval, limit=20)
    response = await client.get(case.rest_path, params=params)

    assert response.status == 200
    candles = adapter._parse_rest_response(await response.json())
    stored = {c.timestamp: c for c in server.candles[case.pair][case.interval]}
    assert 0 < len(candles) <= 200
    for parsed in candles:
        assert parsed.close == pytest.approx(stored[parsed.timestamp].close)


@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_rest_limit_is_honoured(case, make_server, aiohttp_client):
    if case.exchange_type in (ExchangeType.DEXALOT_SPOT, ExchangeType.BITMART_PERPETUAL):
        pytest.skip("endpoint has no limit parameter")
    server = make_server(case)
    client = await aiohttp_client(server.app)
    adapter = case.plugin_cls().adapter_class()

    params = adapter._get_rest_params(case.pair, case.interval, limit=5)
    params.pop("startTime", None)
    params.pop("endTime", None)
    params.pop("start_time", None)
    params.pop("end_time", None)
    candles = adapter._parse_rest_response(
        await (await client.get(case.rest_path, params=params)).json()
    )

    assert len(candles) == 5


@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_rest_unknown_symbol_is_rejected(case, make_server, aiohttp_client):
    server = make_server(case)
    client = await aiohttp_client(server.app)
    adapter = case.plugin_cls().adapter_class()
    other = "ZZZ-USDT" if "AUD" not in case.pair else "ZZZ-AUD"
    path = case.rest_path.replace(case.pair, other)

    params = adapter._get_rest_params(other, case.interval, limit=5)
    response = await client.get(path, params=params)

    assert response.status == 400


@pytest.mark.parametrize("case", WS_CASES, ids=WS_IDS)
async def test_ws_subscription_streams_current_candle_and_unsubscribes(
    case, make_server, aiohttp_client
):
    server = make_server(case)
    client = await aiohttp_client(server.app)
    adapter = case.plugin_cls().adapter_class()
    payload = adapter.get_ws_subscription_payload(case.pair, case.interval)

    ws = await client.ws_connect("/ws")
    await ws.send_json(payload)
    # The server answers a subscription with the current candle and an acknowledgement.
    replies = [await asyncio.wait_for(ws.receive_json(), timeout=3) for _ in range(2)]
    parsed = [c for reply in replies if (c := adapter.parse_ws_message(reply))]

    assert len(parsed) == 1, f"expected one candle among {replies}"
    assert parsed[0][0].timestamp == server.candles[case.pair][case.interval][-1].timestamp
    assert any(server.subscriptions.values())

    await ws.send_json(unsubscribe_variant(payload))
    ack = await asyncio.wait_for(ws.receive_json(), timeout=3)
    assert adapter.parse_ws_message(ack) is None
    assert not any(server.subscriptions.values())
    await ws.close()


@pytest.mark.parametrize("case", WS_CASES, ids=WS_IDS)
async def test_ws_malformed_json_gets_an_error_reply(case, make_server, aiohttp_client):
    client = await aiohttp_client(make_server(case).app)
    ws = await client.ws_connect("/ws")
    await ws.send_str("{not json")
    assert (await asyncio.wait_for(ws.receive_json(), timeout=3)) == {"error": "Invalid JSON"}
    await ws.close()


@pytest.mark.parametrize("case", WS_CASES, ids=WS_IDS)
def test_ws_message_and_subscription_helpers(case):
    plugin = case.plugin_cls()
    adapter = plugin.adapter_class()
    payload = adapter.get_ws_subscription_payload(case.pair, case.interval)

    (_pair, interval), *rest = plugin.parse_ws_subscription(payload)
    assert not rest
    assert interval in adapter.get_supported_intervals() or interval == "1m"
    assert plugin.parse_ws_subscription({"op": "subscribe", "data": ["nonsense"]}) == []
    assert plugin.is_ws_unsubscribe(unsubscribe_variant(payload))
    assert not plugin.is_ws_unsubscribe(payload)
    assert isinstance(plugin.create_ws_subscription_success(payload, [("X", "1m")]), dict)
    assert plugin.create_ws_subscription_key(case.pair, case.interval)


def test_btc_markets_has_no_websocket():
    plugin = BTCMarketsSpotPlugin()
    assert plugin.ws_routes == {}
    assert plugin.parse_ws_subscription({"op": "subscribe"}) == []
    assert plugin.create_ws_subscription_success({}, []) == {}
    assert plugin.create_ws_subscription_key("BTC-AUD", "1m") == "BTC-AUD_1m"
    with pytest.raises(NotImplementedError):
        plugin.format_ws_candle_message(None, "BTC-AUD", "1m")  # type: ignore[arg-type]


async def test_websocket_handler_rejects_when_rate_limited(make_server, aiohttp_client):
    server = make_server(CASES[0])
    server.rate_limits["ws"]["limit"] = 0
    client = await aiohttp_client(server.app)
    response = await client.get("/ws")
    assert response.status == 429
