"""
Behavioural coverage tests for MockedPlugin handlers and helpers.
"""

import asyncio
import json
import logging

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer, make_mocked_request

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin import MockedPlugin

T0 = 1620000000


def make_candle(i: int) -> CandleData:
    return CandleData(
        timestamp_raw=T0 + 60 * i,
        open=10.0 + i,
        high=12.0 + i,
        low=9.0 + i,
        close=11.0 + i,
        volume=2.0,
        quote_asset_volume=0.0 if i == 0 else 20.0,
        n_trades=5,
        taker_buy_base_volume=1.0,
        taker_buy_quote_volume=2.0,
    )


class FakeServer:
    def __init__(self, allow: bool = True, latency_ms: int = 0):
        self.allow = allow
        self.latency_ms = latency_ms
        self.candles = {"BTC-USDT": {"1m": [make_candle(i) for i in range(5)]}}
        self.trading_pairs = {"BTC-USDT": 1.0, "ETHBTCX": 1.0}
        self.subscriptions: dict = {}
        self.ws_connections: set = set()
        self.logger = logging.getLogger("fake")

    async def _simulate_network_conditions(self):
        return None

    def _check_rate_limit(self, ip, kind):
        return self.allow

    def _time(self):
        return 1700000000.0


@pytest.fixture
def plugin():
    return MockedPlugin()


@pytest.fixture
def server():
    return FakeServer()


def req(path: str):
    return make_mocked_request("GET", path)


def body(resp: web.Response):
    return json.loads(resp.text)


class TestHelpers:
    def test_urls_and_routes(self, plugin):
        assert plugin.rest_url == "https://mock-exchange.test/api"
        assert plugin.wss_url == "wss://mock-exchange.test/ws"
        assert plugin.ws_routes == {"/ws": "handle_websocket"}
        assert plugin.rest_routes["/api/v3/ping"] == ("GET", "handle_ping")

    def test_format_rest_candles_quote_volume_branches(self, plugin):
        out = plugin.format_rest_candles([make_candle(0), make_candle(1)], "BTC-USDT", "1m")
        zero, nonzero = out["data"]
        assert zero["quote_volume"] == "0"
        assert zero["taker_quote_volume"] == "0"
        assert nonzero["quote_volume"] == "20.0"
        assert nonzero["taker_quote_volume"] == str(20.0 * 0.7)
        assert nonzero["close_time"] == (T0 + 60) * 1000 + 60_000

    def test_format_ws_candle_message(self, plugin):
        msg = plugin.format_ws_candle_message(make_candle(0), "BTC-USDT", "1m", is_final=True)
        assert msg["type"] == "candle_update"
        assert msg["is_final"] is True
        assert msg["data"]["quote_volume"] == "0"
        msg = plugin.format_ws_candle_message(make_candle(1), "BTC-USDT", "1m")
        assert msg["is_final"] is False
        assert msg["data"]["quote_volume"] == "20.0"

    def test_parse_ws_subscription_own_format(self, plugin):
        msg = {
            "type": "subscribe",
            "subscriptions": [
                {"symbol": "BTC-USDT", "interval": "1m"},
                {"symbol": "ETH-USDT"},
            ],
        }
        assert plugin.parse_ws_subscription(msg) == [("BTC-USDT", "1m")]

    def test_parse_ws_subscription_binance_format(self, plugin):
        msg = {"method": "SUBSCRIBE", "params": ["btcusdt@kline_1m", "bad", "x@kline_1m@kline_2m"]}
        assert plugin.parse_ws_subscription(msg) == [("BTCUSDT", "1m")]
        assert plugin.parse_ws_subscription({"method": "NOPE"}) == []

    def test_subscription_success(self, plugin):
        assert plugin.create_ws_subscription_success(
            {"method": "SUBSCRIBE", "id": 5}, [("A", "1m")]
        ) == {"result": None, "id": 5}
        out = plugin.create_ws_subscription_success({"type": "subscribe"}, [("A-B", "1m")])
        assert out["subscriptions"] == [{"symbol": "A-B", "interval": "1m"}]
        assert plugin.create_ws_subscription_key("A-B", "1m") == "A-B_1m"

    def test_trading_pairs_and_base_price(self, plugin):
        assert plugin.get_base_price("BTC-USDT") == 100.0
        plugin.add_trading_pair("BTC-USDT", "1m", 5.0)
        plugin.add_trading_pair("BTC-USDT", "5m", 6.0)
        assert plugin.get_base_price("BTC-USDT") == 5.0
        assert plugin.get_base_price("ETH-USDT") == 100.0
        plugin.trading_pairs["EMPTY"] = {}
        assert plugin.get_base_price("EMPTY") == 100.0

    @pytest.mark.parametrize(
        ("pair", "expected"),
        [
            ("BTC-USDT", "BTC-USDT"),
            ("BTCUSDT", "BTC-USDT"),
            ("ETHBTC", "ETH-BTC"),
            ("SOLXYZW", "SOL-XYZW"),
            ("ABCD", "ABCD"),
        ],
    )
    def test_normalize_trading_pair(self, plugin, pair, expected):
        assert plugin.normalize_trading_pair(pair) == expected

    @pytest.mark.parametrize(
        ("interval", "seconds"),
        [
            ("5s", 5),
            ("2m", 120),
            ("1h", 3600),
            ("1d", 86400),
            ("1w", 604800),
            ("1x", 60),
            ("abm", 60),
        ],
    )
    def test_interval_seconds(self, plugin, interval, seconds):
        assert plugin.get_interval_seconds(interval) == seconds
        assert plugin._interval_to_milliseconds(interval) == seconds * 1000

    def test_parse_rest_candles_params_invalid_limit(self, plugin):
        p = plugin.parse_rest_candles_params(req("/c?symbol=X&limit=abc"))
        assert p["limit"] == 1000
        assert p["interval"] is None
        p = plugin.parse_rest_candles_params(req("/c?symbol=X"))
        assert p["limit"] is None


class TestRestHandlers:
    @pytest.mark.parametrize(
        "name", ["handle_time", "handle_instruments", "handle_ping", "handle_klines"]
    )
    async def test_rate_limited(self, plugin, name):
        resp = await getattr(plugin, name)(FakeServer(allow=False), req("/x"))
        assert resp.status == 429
        assert body(resp) == {"error": "Rate limit exceeded"}

    async def test_time_and_ping(self, plugin, server):
        data = body(await plugin.handle_time(server, req("/t")))
        assert data == {"status": "ok", "timestamp": 1700000000000, "server_time": 1700000000000}
        assert body(await plugin.handle_ping(server, req("/p"))) == {}

    async def test_instruments(self, plugin, server):
        data = body(await plugin.handle_instruments(server, req("/i")))
        by_symbol = {i["symbol"]: i for i in data["instruments"]}
        assert by_symbol["BTC-USDT"]["base_asset"] == "BTC"
        assert by_symbol["BTC-USDT"]["quote_asset"] == "USDT"
        assert by_symbol["ETHBTCX"]["base_asset"] == "ETH"
        assert by_symbol["ETHBTCX"]["quote_asset"] == "BTCX"

    async def test_klines_exact_and_limit(self, plugin, server):
        data = body(
            await plugin.handle_klines(server, req("/k?symbol=BTCUSDT&interval=1m&limit=2"))
        )
        assert data["symbol"] == "BTC-USDT"
        assert [c["timestamp"] for c in data["data"]] == [(T0 + 180) * 1000, (T0 + 240) * 1000]

    async def test_klines_case_insensitive_symbol(self, plugin, server):
        data = body(await plugin.handle_klines(server, req("/k?symbol=btc-usdt&interval=1m")))
        assert len(data["data"]) == 5
        data = body(await plugin.handle_klines(server, req("/k?symbol=btcusdt&interval=1m")))
        assert len(data["data"]) == 5

    async def test_klines_errors(self, plugin, server):
        resp = await plugin.handle_klines(server, req("/k?interval=1m"))
        assert resp.status == 404 and "Symbol not found" in body(resp)["error"]
        resp = await plugin.handle_klines(server, req("/k?symbol=NOPE&interval=1m"))
        assert resp.status == 404
        resp = await plugin.handle_klines(server, req("/k?symbol=BTCUSDT"))
        assert resp.status == 404 and "Interval not found" in body(resp)["error"]
        resp = await plugin.handle_klines(server, req("/k?symbol=BTCUSDT&interval=9h"))
        assert resp.status == 404


@pytest.fixture
async def ws_env(plugin, server):
    app = web.Application()

    async def handler(request):
        return await plugin.handle_websocket(server, request)

    app.router.add_get("/ws", handler)
    client = TestClient(TestServer(app))
    await client.start_server()
    try:
        yield client, server
    finally:
        await client.close()


class TestWebSocket:
    async def test_own_format_subscribe_and_unsubscribe(self, ws_env):
        client, server = ws_env
        ws = await client.ws_connect("/ws")
        await ws.send_json(
            {"type": "subscribe", "subscriptions": [{"symbol": "BTCUSDT", "interval": "1m"}]}
        )
        ack = await ws.receive_json()
        assert ack["type"] == "subscribe_result"
        assert ack["subscriptions"] == [{"symbol": "BTCUSDT", "interval": "1m"}]
        update = await ws.receive_json()
        assert update["type"] == "candle_update"
        assert update["symbol"] == "BTC-USDT"
        assert update["is_final"] is True
        assert len(server.subscriptions["BTC-USDT_1m"]) == 1

        await ws.send_json(
            {"type": "unsubscribe", "subscriptions": [{"symbol": "BTCUSDT", "interval": "1m"}]}
        )
        unsub_ack = await ws.receive_json()
        assert unsub_ack["type"] == "unsubscribe_result"
        assert unsub_ack["subscriptions"] == [{"symbol": "BTCUSDT", "interval": "1m"}]
        assert "BTC-USDT_1m" not in server.subscriptions

        await ws.close()

    async def test_binance_format_subscribe(self, ws_env):
        client, server = ws_env
        server.candles["BTC-USDT"]["5m"] = []
        ws = await client.ws_connect("/ws")
        await ws.send_json(
            {"method": "SUBSCRIBE", "params": ["btcusdt@kline_5m", "nopeusdt@kline_1m"], "id": 11}
        )
        assert await ws.receive_json() == {"result": None, "id": 11}
        # only the known pair/interval is tracked, and it has no candle to push
        assert set(server.subscriptions) == {"BTC-USDT_5m"}
        # an UNSUBSCRIBE is acknowledged and removes the subscription
        await ws.send_json({"method": "UNSUBSCRIBE", "params": ["btcusdt@kline_5m"], "id": 12})
        assert await ws.receive_json() == {"result": None, "id": 12}
        assert "BTC-USDT_5m" not in server.subscriptions
        await ws.close()

    async def test_invalid_json_and_internal_error(self, ws_env):
        client, _ = ws_env
        ws = await client.ws_connect("/ws")
        await ws.send_str("garbage")
        assert await ws.receive_json() == {"error": "Invalid JSON"}
        await ws.send_json({"method": "SUBSCRIBE", "params": 5})
        assert (await ws.receive_json())["error"].startswith("Error:")
        await ws.send_json({"type": "ignored"})
        await ws.close()

    async def test_rate_limited_connection(self, plugin):
        server = FakeServer(allow=False)
        resp = await plugin.handle_websocket(server, req("/ws"))
        assert resp.status == 429

    async def test_latency_applied(self, plugin, monkeypatch):
        slept: list[float] = []

        async def fake_sleep(delay):
            slept.append(delay)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        resp = await plugin.handle_websocket(FakeServer(allow=False, latency_ms=250), req("/ws"))
        assert resp.status == 429
        assert slept == [0.25]

    async def test_disconnect_cleans_up(self, ws_env):
        client, server = ws_env
        ws = await client.ws_connect("/ws")
        await ws.send_json(
            {"type": "subscribe", "subscriptions": [{"symbol": "BTC-USDT", "interval": "1m"}]}
        )
        await ws.receive_json()
        await ws.receive_json()
        await ws.close()
        for _ in range(100):
            if not server.ws_connections:
                break
            await asyncio.sleep(0.01)
        assert not server.ws_connections
        assert server.subscriptions == {}
