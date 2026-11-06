"""Behaviour tests for BybitBasePlugin handlers and formatters (called directly)."""

import json

import pytest
from aiohttp.test_utils import make_mocked_request

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.exchange_server_plugins.bybit.base_plugin import (
    BybitBasePlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.bybit.spot_plugin import BybitSpotPlugin


class FakeServer:
    """Minimal stand-in for the mock exchange server used by the plugin handlers."""

    def __init__(self, candles=None, allow=True, now=1_700_000_000.5):
        self.candles = candles or {}
        self.allow = allow
        self.now = now
        self.simulated = 0
        self.rate_checks = []
        self.ws_calls = []

    async def _simulate_network_conditions(self):
        self.simulated += 1

    def _check_rate_limit(self, client_ip, kind):
        self.rate_checks.append((client_ip, kind))
        return self.allow

    def _time(self):
        return self.now

    async def _handle_websocket_connection(self, websocket, plugin):
        self.ws_calls.append((websocket, plugin))


def make_candles(count=5, start=1_700_000_000, step=60):
    return [
        CandleData(
            timestamp_raw=start + i * step,
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=10.0 + i,
            quote_asset_volume=1000.0 + i,
        )
        for i in range(count)
    ]


@pytest.fixture
def plugin():
    return BybitSpotPlugin()


@pytest.fixture
def server():
    return FakeServer({"BTC-USDT": {"1m": make_candles()}})


def body(response):
    return json.loads(response.text)


@pytest.mark.parametrize(
    ("interval", "seconds"),
    [("30s", 30), ("5m", 300), ("2h", 7200), ("1d", 86400), ("2w", 1209600)],
)
def test_interval_to_seconds(interval, seconds):
    assert BybitBasePlugin._interval_to_seconds(interval) == seconds


def test_interval_to_seconds_unknown_unit_raises():
    with pytest.raises(ValueError, match="Unknown interval unit: x"):
        BybitBasePlugin._interval_to_seconds("5x")


def test_urls_and_routes_come_from_adapter_constants(plugin):
    assert BybitBasePlugin.rest_url.fget(plugin).startswith("https://")
    assert BybitBasePlugin.wss_url.fget(plugin).startswith("wss://")
    assert BybitBasePlugin.ws_routes.fget(plugin) == {"/ws": "handle_websocket"}


def test_format_rest_candles_rows_and_envelope(plugin):
    candles = make_candles(2)
    out = BybitBasePlugin.format_rest_candles(plugin, candles, "BTC-USDT", "1m")
    assert out["retCode"] == 0
    assert out["result"]["symbol"] == "BTCUSDT"
    assert out["time"] == candles[0].timestamp_ms
    assert out["result"]["list"][1] == [
        str(candles[1].timestamp_ms),
        "101.0",
        "102.0",
        "100.0",
        "101.5",
        "11.0",
        "1001.0",
    ]


def test_format_rest_candles_empty_has_zero_time(plugin):
    out = BybitBasePlugin.format_rest_candles(plugin, [], "BTC-USDT", "1m")
    assert out["result"]["list"] == []
    assert out["time"] == 0


@pytest.mark.parametrize(
    ("interval", "code", "span_ms"),
    [("1m", "1", 60_000), ("1h", "60", 3_600_000), ("1d", "D", 86_400_000)],
)
def test_format_ws_candle_message_end_time_by_unit(plugin, interval, code, span_ms):
    candle = make_candles(1)[0]
    msg = BybitBasePlugin.format_ws_candle_message(
        plugin, candle, "BTC-USDT", interval, is_final=True
    )
    row = msg["data"][0]
    assert msg["topic"] == f"kline.{code}.BTCUSDT"
    assert row["interval"] == code
    assert row["end"] - row["start"] == span_ms
    assert row["confirm"] is True
    assert row["open"] == "100.0"
    assert msg["ts"] == candle.timestamp_ms


def test_parse_ws_subscription_converts_topic_to_pair_and_interval(plugin):
    message = {"op": "subscribe", "args": ["kline.60.ETHBTC", "kline.1.BTCUSDT"]}
    assert BybitBasePlugin.parse_ws_subscription(plugin, message) == [
        ("ETH-BTC", "1h"),
        ("BTC-USDT", "1m"),
    ]


def test_parse_ws_subscription_ignores_non_subscribe_and_other_topics(plugin):
    assert BybitBasePlugin.parse_ws_subscription(plugin, {"op": "ping"}) == []
    msg = {"op": "subscribe", "args": ["orderbook.50.BTCUSDT", "kline.1", "kline.1.2.3"]}
    assert BybitBasePlugin.parse_ws_subscription(plugin, msg) == []


def test_parse_ws_subscription_keeps_unsplittable_pair_and_unknown_interval(plugin):
    msg = {"op": "subscribe", "args": ["kline.99.ABCDEF", "kline.1.AB"]}
    assert BybitBasePlugin.parse_ws_subscription(plugin, msg) == [("ABCDEF", "99"), ("AB", "1m")]


def test_subscription_success_echoes_args(plugin):
    message = {"op": "subscribe", "args": ["kline.1.BTCUSDT"]}
    out = BybitBasePlugin.create_ws_subscription_success(plugin, message, [("BTC-USDT", "1m")])
    assert out["success"] is True
    assert out["args"] == ["kline.1.BTCUSDT"]
    assert BybitBasePlugin.create_ws_subscription_success(plugin, {}, [])["args"] == []


def test_subscription_key(plugin):
    assert BybitBasePlugin.create_ws_subscription_key(plugin, "BTC-USDT", "1h") == (
        "kline.60.BTCUSDT"
    )
    assert BybitBasePlugin.create_ws_subscription_key(plugin, "BTC-USDT", "9z") == (
        "kline.9z.BTCUSDT"
    )


def test_parse_rest_params_invalid_limit_falls_back(plugin):
    request = make_mocked_request("GET", "/v5/market/kline?symbol=BTCUSDT&limit=abc")
    params = BybitBasePlugin.parse_rest_candles_params(plugin, request)
    assert params["limit"] == 1000
    assert params["interval"] is None
    assert params["start_time"] is None


def test_parse_rest_params_without_limit(plugin):
    request = make_mocked_request("GET", "/v5/market/kline?symbol=BTCUSDT")
    assert BybitBasePlugin.parse_rest_candles_params(plugin, request)["limit"] is None


async def test_handle_time_returns_server_time(plugin, server):
    response = await BybitBasePlugin.handle_time(plugin, server, make_mocked_request("GET", "/t"))
    data = body(response)
    assert response.status == 200
    assert data["result"]["timeSecond"] == "1700000000"
    assert data["time"] == 1_700_000_000_500
    assert server.simulated == 1
    assert server.rate_checks[0][1] == "rest"


async def test_handle_time_rate_limited(plugin):
    server = FakeServer(allow=False)
    response = await BybitBasePlugin.handle_time(plugin, server, make_mocked_request("GET", "/t"))
    assert response.status == 429
    assert body(response) == {"error": "Rate limit exceeded"}


async def test_handle_klines_rate_limited(plugin):
    server = FakeServer(allow=False)
    response = await BybitBasePlugin.handle_klines(
        plugin, server, make_mocked_request("GET", "/k?symbol=BTCUSDT&interval=1")
    )
    assert response.status == 429
    assert body(response)["retCode"] == 10004


@pytest.mark.parametrize("query", ["", "?symbol=BTCUSDT", "?interval=1"])
async def test_handle_klines_missing_params(plugin, server, query):
    response = await BybitBasePlugin.handle_klines(
        plugin, server, make_mocked_request("GET", f"/k{query}")
    )
    assert response.status == 400
    assert body(response)["retMsg"] == "Missing required parameters"


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ("symbol=ETHUSDT&interval=1", "Invalid symbol: ETHUSDT"),
        ("symbol=BTCUSDT&interval=zzz", "Invalid interval: zzz"),
        ("symbol=BTCUSDT&interval=5", "Invalid interval: 5m"),
    ],
)
async def test_handle_klines_invalid_symbol_or_interval(plugin, server, query, message):
    response = await BybitBasePlugin.handle_klines(
        plugin, server, make_mocked_request("GET", f"/k?{query}")
    )
    assert response.status == 400
    assert body(response)["retMsg"] == message


async def test_handle_klines_returns_all_candles(plugin, server):
    request = make_mocked_request("GET", "/k?symbol=BTCUSDT&interval=1&limit=0")
    response = await BybitBasePlugin.handle_klines(plugin, server, request)
    assert response.status == 200
    assert len(body(response)["result"]["list"]) == 5


async def test_handle_klines_filters_by_time_and_limit(plugin, server):
    first = server.candles["BTC-USDT"]["1m"][0].timestamp_ms
    start, end = first + 60_000, first + 240_000
    request = make_mocked_request(
        "GET", f"/k?symbol=BTCUSDT&interval=1&start={start}&end={end}&limit=2"
    )
    response = await BybitBasePlugin.handle_klines(plugin, server, request)
    rows = body(response)["result"]["list"]
    assert [int(r[0]) for r in rows] == [first + 180_000, first + 240_000]


async def test_handle_instruments_lists_symbols(plugin, server):
    response = await BybitBasePlugin.handle_instruments(
        plugin, server, make_mocked_request("GET", "/i")
    )
    items = body(response)["result"]["list"]
    assert [(i["symbol"], i["baseCoin"], i["quoteCoin"]) for i in items] == [
        ("BTCUSDT", "BTC", "USDT")
    ]


async def test_handle_instruments_rate_limited(plugin):
    response = await BybitBasePlugin.handle_instruments(
        plugin, FakeServer(allow=False), make_mocked_request("GET", "/i")
    )
    assert response.status == 429


async def test_handle_websocket_delegates_to_server(plugin, server):
    sentinel = object()
    await BybitBasePlugin.handle_websocket(plugin, server, sentinel, "/ws")
    assert server.ws_calls == [(sentinel, plugin)]
