"""
Behavioural coverage tests for BinanceBasePlugin (exercised via BinanceSpotPlugin).
"""

import asyncio
import json
import logging

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer, make_mocked_request

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.exchange_server_plugins.binance.base_plugin import (
    BinanceBasePlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import (
    BinanceSpotPlugin,
)

T0 = 1620000000


def make_candle(i: int, close: float = 100.0) -> CandleData:
    return CandleData(
        timestamp_raw=T0 + 60 * i,
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=10.0,
        quote_asset_volume=1000.0,
        n_trades=5,
        taker_buy_base_volume=1.0,
        taker_buy_quote_volume=2.0,
    )


class FakeServer:
    def __init__(self, allow: bool = True, auth: dict | None = None):
        self.allow = allow
        self.auth = auth or {"authenticated": True}
        self.candles = {"BTC-USDT": {"1m": [make_candle(i, 100.0 + i) for i in range(5)]}}
        self.trading_pairs = {"BTC-USDT": 100.0, "ETHBTC": 1.0}
        self.subscriptions: dict = {}
        self.ws_connections: set = set()
        self.rate_limits = {"rest": {"limit": 777}}
        self.logger = logging.getLogger("fake")
        self.rate_checks: list = []

    async def _simulate_network_conditions(self):
        return None

    def _check_rate_limit(self, ip, kind):
        self.rate_checks.append(kind)
        return self.allow

    def _time(self):
        return 1700000000.0

    def verify_authentication(self, request, required_permissions=None):
        return self.auth


class BaseBehaviourPlugin(BinanceSpotPlugin):
    """Concrete plugin that uses the base-class klines parameter parser (spot overrides it)."""

    parse_rest_candles_params = BinanceBasePlugin.parse_rest_candles_params


@pytest.fixture
def plugin():
    return BaseBehaviourPlugin()


@pytest.fixture
def server():
    return FakeServer()


def req(path: str):
    return make_mocked_request("GET", path)


def body(resp: web.Response):
    return json.loads(resp.text)


class TestStaticProperties:
    def test_rate_limits_and_keys(self, plugin):
        limits = plugin.rate_limits
        assert limits["rest"]["weights"]["/api/v3/klines"] == 2
        assert limits["ws"]["connection_limit"] == 50
        assert "TESTKEY123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" in plugin.api_keys
        assert plugin.network_settings["websocket_keep_alive"]["interval_seconds"] == 180
        assert plugin.ws_routes == {"/ws": "handle_websocket"}
        assert plugin.rest_url.startswith("https://")
        assert plugin.wss_url.startswith("wss://")


class TestHelpers:
    @pytest.mark.parametrize(
        ("interval", "expected"),
        [
            ("1m", 60_000),
            ("2h", 7_200_000),
            ("1d", 86_400_000),
            ("1w", 604_800_000),
            ("5x", 60_000),
        ],
    )
    def test_interval_to_milliseconds(self, plugin, interval, expected):
        assert plugin._interval_to_milliseconds(interval) == expected

    @pytest.mark.parametrize(
        ("interval", "expected"),
        [("30s", 30), ("1m", 60), ("1h", 3600), ("1d", 86400), ("1w", 604800)],
    )
    def test_interval_to_seconds(self, interval, expected):
        assert BinanceSpotPlugin._interval_to_seconds(interval) == expected

    def test_interval_to_seconds_unknown_unit(self):
        with pytest.raises(ValueError, match="Unknown interval unit"):
            BinanceSpotPlugin._interval_to_seconds("1x")

    def test_format_rest_candles_with_tz(self, plugin):
        rows = plugin.format_rest_candles([make_candle(0)], "BTC-USDT", "1m", 3_600_000)
        row = rows[0]
        assert row[0] == T0 * 1000 + 3_600_000
        assert row[6] == T0 * 1000 + 60_000 + 3_600_000
        assert row[1] == "99.0"
        assert row[5] == "10.0"
        assert row[9] == str(10.0 * 0.7)

    def test_format_ws_candle_message(self, plugin):
        msg = plugin.format_ws_candle_message(make_candle(0), "BTC-USDT", "1m", is_final=True)
        assert msg["e"] == "kline"
        assert msg["s"] == "BTCUSDT"
        assert msg["k"]["x"] is True
        assert msg["k"]["T"] == T0 * 1000 + 60_000
        assert msg["k"]["i"] == "1m"

    def test_parse_ws_subscription(self, plugin):
        msg = {
            "method": "SUBSCRIBE",
            "params": ["btcusdt@kline_1m", "ethbtc@kline_5m", "junk", "a@kline_1m@kline_2m"],
        }
        assert plugin.parse_ws_subscription(msg) == [("BTC-USDT", "1m"), ("ETH-BTC", "5m")]

    def test_parse_ws_subscription_non_subscribe(self, plugin):
        assert plugin.parse_ws_subscription({"method": "OTHER"}) == []

    def test_subscription_success_and_key(self, plugin):
        assert plugin.create_ws_subscription_success({"id": 9}, []) == {"result": None, "id": 9}
        assert plugin.create_ws_subscription_success({}, [])["id"] == 1
        assert plugin.create_ws_subscription_key("BTC-USDT", "1m") == "btcusdt@kline_1m"


class TestParseRestCandlesParams:
    def test_valid_defaults(self, plugin):
        p = plugin.parse_rest_candles_params(req("/k?symbol=BTCUSDT&interval=1m"))
        assert p["valid"] is True
        assert p["limit"] == 500
        assert p["timezone_offset_hours"] == 0

    def test_limit_capped(self, plugin):
        p = plugin.parse_rest_candles_params(req("/k?symbol=BTCUSDT&interval=1m&limit=5000"))
        assert p["limit"] == 1000

    @pytest.mark.parametrize(
        ("query", "code"),
        [
            ("interval=1m", -1102),
            ("symbol=BTCUSDT", -1120),
            ("symbol=BTCUSDT&interval=7m", -1121),
            ("symbol=BTCUSDT&interval=1m&startTime=5&endTime=5", -1125),
            ("symbol=BTCUSDT&interval=1m&startTime=a&endTime=b", -1104),
            ("symbol=BTCUSDT&interval=1m&limit=0", -1127),
            ("symbol=BTCUSDT&interval=1m&limit=abc", -1128),
            ("symbol=BTCUSDT&interval=1m&timeZone=20", -1130),
            ("symbol=BTCUSDT&interval=1m&timeZone=zz", -1130),
        ],
    )
    def test_errors(self, plugin, query, code):
        p = plugin.parse_rest_candles_params(req(f"/k?{query}"))
        assert p["valid"] is False
        assert p["error"]["code"] == code

    def test_timezone_with_minutes(self, plugin):
        p = plugin.parse_rest_candles_params(req("/k?symbol=BTCUSDT&interval=1m&timeZone=5:30"))
        assert p["timezone_offset_hours"] == 5.5


class TestRestHandlers:
    async def test_ping_time(self, plugin, server):
        assert body(await plugin.handle_ping(server, req("/p"))) == {}
        assert body(await plugin.handle_time(server, req("/t"))) == {"serverTime": 1700000000000}

    @pytest.mark.parametrize(
        ("name", "path"),
        [
            ("handle_ping", "/p"),
            ("handle_time", "/t"),
            ("handle_exchange_info", "/e"),
            ("handle_klines", "/k"),
            ("handle_depth", "/d"),
            ("handle_ticker_price", "/tp"),
            ("handle_account", "/a"),
            ("handle_instruments", "/i"),
        ],
    )
    async def test_rate_limited(self, plugin, name, path):
        resp = await getattr(plugin, name)(FakeServer(allow=False), req(path))
        assert resp.status == 429

    async def test_exchange_info(self, plugin, server):
        server.candles["BTCUSDT_LONGX"] = {}
        server.candles["ETHBTC"] = {}
        data = body(await plugin.handle_exchange_info(server, req("/e")))
        by_symbol = {s["symbol"]: s for s in data["symbols"]}
        assert by_symbol["BTCUSDT"]["baseAsset"] == "BTC"
        assert by_symbol["BTCUSDT"]["quoteAsset"] == "USDT"
        assert by_symbol["ETHBTC"]["baseAsset"] == "ETH"
        assert by_symbol["BTCUSDT_LONGX"]["baseAsset"] == "BTCUSDT_L"
        assert data["rateLimits"][0]["limit"] == 777

    async def test_klines_ok_with_filters(self, plugin, server):
        start = (T0 + 60) * 1000
        end = (T0 + 180) * 1000
        resp = await plugin.handle_klines(
            server, req(f"/k?symbol=BTCUSDT&interval=1m&startTime={start}&endTime={end}")
        )
        rows = body(resp)
        assert [r[0] for r in rows] == [(T0 + 60) * 1000, (T0 + 120) * 1000, (T0 + 180) * 1000]

    async def test_klines_seconds_and_limit_and_tz(self, plugin, server):
        resp = await plugin.handle_klines(
            server,
            req(
                f"/k?symbol=BTCUSDT&interval=1m&startTime={T0}&endTime={T0 + 600}&limit=2&timeZone=1"
            ),
        )
        rows = body(resp)
        assert len(rows) == 2
        assert rows[-1][0] == (T0 + 240) * 1000 + 3_600_000

    async def test_klines_invalid_params(self, plugin, server):
        resp = await plugin.handle_klines(server, req("/k?interval=1m"))
        assert resp.status == 400
        assert body(resp)["code"] == -1102

    async def test_klines_unknown_symbol(self, plugin, server):
        resp = await plugin.handle_klines(server, req("/k?symbol=XYZ&interval=1m"))
        assert resp.status == 400
        assert body(resp)["code"] == -1121

    async def test_klines_unknown_interval(self, plugin, server):
        resp = await plugin.handle_klines(server, req("/k?symbol=BTCUSDT&interval=5m"))
        assert resp.status == 400
        assert body(resp)["code"] == -1120

    async def test_klines_async_parser(self, plugin, server, monkeypatch):
        async def parse(request):
            return {"valid": False, "error": {"msg": "async bad"}}

        monkeypatch.setattr(plugin, "parse_rest_candles_params", parse)
        resp = await plugin.handle_klines(server, req("/k"))
        assert resp.status == 400
        assert body(resp) == {"msg": "async bad"}

    async def test_depth_ok(self, plugin, server):
        data = body(await plugin.handle_depth(server, req("/d?symbol=btcusdt&limit=3")))
        assert len(data["bids"]) == 3 and len(data["asks"]) == 3
        assert float(data["bids"][0][0]) < 104.0 < float(data["asks"][0][0])
        assert float(data["bids"][0][0]) > float(data["bids"][2][0])

    async def test_depth_limit_capped_and_default_price(self, plugin, server):
        server.candles["BTC-USDT"] = {"1m": []}
        data = body(await plugin.handle_depth(server, req("/d?symbol=BTCUSDT&limit=9999")))
        assert len(data["bids"]) == 5000
        assert float(data["asks"][0][0]) == pytest.approx(50000.0 * 1.0001)

    @pytest.mark.parametrize(
        ("query", "code"),
        [("", -1102), ("symbol=BTCUSDT&limit=0", -1100), ("symbol=BTCUSDT&limit=x", -1100)],
    )
    async def test_depth_bad_params(self, plugin, server, query, code):
        resp = await plugin.handle_depth(server, req(f"/d?{query}"))
        assert resp.status == 400
        assert body(resp)["code"] == code

    async def test_depth_unknown_symbol(self, plugin, server):
        resp = await plugin.handle_depth(server, req("/d?symbol=NOPE"))
        assert resp.status == 400
        assert body(resp)["code"] == -1121

    async def test_ticker_single(self, plugin, server):
        data = body(await plugin.handle_ticker_price(server, req("/tp?symbol=btcusdt")))
        assert data == {"symbol": "BTCUSDT", "price": "104.00000000"}

    async def test_ticker_single_unknown_and_default(self, plugin, server):
        resp = await plugin.handle_ticker_price(server, req("/tp?symbol=NOPE"))
        assert resp.status == 400
        server.candles["BTC-USDT"] = {}
        data = body(await plugin.handle_ticker_price(server, req("/tp?symbol=BTCUSDT")))
        assert data["price"] == "50000.00000000"

    async def test_ticker_all(self, plugin, server):
        data = body(await plugin.handle_ticker_price(server, req("/tp")))
        prices = {d["symbol"]: d["price"] for d in data}
        assert prices["BTCUSDT"] == "104.00000000"
        assert prices["ETHBTC"] == "50000.00000000"

    async def test_account(self, plugin, server):
        server.trading_pairs = {"BTC-USDT": 1.0, "XRP-USDT": 1.0}
        data = body(await plugin.handle_account(server, req("/a")))
        assets = [b["asset"] for b in data["balances"]]
        assert assets.count("BTC") == 1
        assert "XRP" in assets
        assert data["accountType"] == "SPOT"

    async def test_account_unauthenticated(self, plugin):
        server = FakeServer(auth={"authenticated": False, "error": {"code": -2015}})
        resp = await plugin.handle_account(server, req("/a"))
        assert resp.status == 401
        assert body(resp) == {"code": -2015}

    async def test_instruments(self, plugin, server):
        server.trading_pairs = {"BTC-USDT": 1.0}
        data = body(await plugin.handle_instruments(server, req("/i?instType=SPOT")))
        inst = data["data"][0]
        assert inst["instId"] == "BTC/USDT"
        assert inst["baseCcy"] == "BTC"
        assert inst["quoteCcy"] == "USDT"
        assert inst["instType"] == "SPOT"

    async def test_instruments_requires_type(self, plugin, server):
        resp = await plugin.handle_instruments(server, req("/i"))
        assert resp.status == 400


@pytest.fixture
async def ws_env(plugin, server):
    app = web.Application()

    async def handler(request):
        return await plugin.handle_websocket(server, request)

    app.router.add_get("/ws", handler)
    test_server = TestServer(app)
    client = TestClient(test_server)
    await client.start_server()
    try:
        yield client, server
    finally:
        await client.close()


class TestWebSocket:
    async def test_subscribe_unsubscribe_flow(self, ws_env):
        client, server = ws_env
        ws = await client.ws_connect("/ws")
        await ws.send_json({"method": "SUBSCRIBE", "params": ["btcusdt@kline_1m"], "id": 7})
        first = await ws.receive_json()
        assert first["e"] == "kline" and first["k"]["x"] is True
        assert first["k"]["c"] == "104.0"
        assert await ws.receive_json() == {"result": None, "id": 7}
        assert len(server.subscriptions["btcusdt@kline_1m"]) == 1

        await ws.send_json({"method": "UNSUBSCRIBE", "params": ["btcusdt@kline_1m"], "id": 8})
        assert await ws.receive_json() == {"result": None, "id": 8}

        await ws.close()

    async def test_subscribe_unknown_pair_and_empty_candles(self, ws_env):
        client, server = ws_env
        server.candles["BTC-USDT"]["5m"] = []
        ws = await client.ws_connect("/ws")
        await ws.send_json(
            {"method": "SUBSCRIBE", "params": ["foousdt@kline_1m", "btcusdt@kline_5m"], "id": 2}
        )
        assert await ws.receive_json() == {"result": None, "id": 2}
        assert set(server.subscriptions) == {"foousdt@kline_1m", "btcusdt@kline_5m"}
        # unsubscribing a key that was never added is harmless
        await ws.send_json({"method": "UNSUBSCRIBE", "params": ["zzzusdt@kline_1m"], "id": 3})
        assert await ws.receive_json() == {"result": None, "id": 3}
        await ws.close()

    async def test_unknown_method_and_bad_input(self, ws_env):
        client, _ = ws_env
        ws = await client.ws_connect("/ws")
        await ws.send_json({"method": "FOO", "id": 4})
        assert await ws.receive_json() == {"error": "Unknown method: FOO", "id": 4}
        await ws.send_json([1, 2])
        assert "expected a JSON object" in (await ws.receive_json())["error"]
        await ws.send_str("not json")
        assert await ws.receive_json() == {"error": "Invalid JSON"}
        await ws.send_json({"method": "SUBSCRIBE", "params": 5})
        assert (await ws.receive_json())["error"].startswith("Error:")
        await ws.close()

    async def test_disconnect_cleans_subscriptions(self, ws_env):
        client, server = ws_env
        ws = await client.ws_connect("/ws")
        await ws.send_json({"method": "SUBSCRIBE", "params": ["btcusdt@kline_1m"], "id": 1})
        await ws.receive_json()
        await ws.receive_json()
        await ws.close()
        for _ in range(50):
            if not server.ws_connections:
                break
            await asyncio.sleep(0.01)
        assert not server.ws_connections
        assert server.subscriptions == {}
