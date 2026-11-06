"""
Behavioural coverage tests for MockedExchangeServer.

The server is exercised through aiohttp's TestServer/TestClient (ephemeral ports),
with a small purpose-built plugin that delegates to the server's own handlers.
"""

import asyncio
import logging
from collections import deque
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.mocking_resources.core import server as server_module
from candles_feed.mocking_resources.core.candle_data_factory import CandleDataFactory
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.server import MockedExchangeServer

NOW = 1_700_000_000.0


class StubWebSocket:
    """Hashable WebSocket stand-in exposing ``request`` and ``send_json``."""

    def __init__(self, request):
        self.request = request
        self.send_json = AsyncMock()


class DelegatingPlugin(ExchangePlugin):
    """Plugin whose handlers delegate to the server's built-in handlers."""

    null_handler = None

    @property
    def rest_routes(self):
        return {
            "/klines": ("GET", "handle_klines"),
            "/time": ("GET", "handle_time"),
            "/ping": ("GET", "handle_ping"),
            "/info": ("GET", "handle_exchange_info"),
            "/post": ("POST", "handle_ping"),
            "/put": ("PUT", "handle_ping"),
            "/delete": ("DELETE", "handle_ping"),
            "/patch": ("PATCH", "handle_ping"),
            "/missing": ("GET", "does_not_exist"),
            "/none": ("GET", "null_handler"),
            "/boom": ("GET", "handle_boom"),
            "/limited": ("GET", "handle_limited"),
            "/limited_hdr": ("GET", "handle_limited_with_header"),
        }

    @property
    def ws_routes(self):
        return {
            "/ws": "handle_websocket",
            "/ws_missing": "does_not_exist",
            "/ws_none": "null_handler",
            "/ws_boom": "handle_boom",
        }

    async def handle_klines(self, server, request):
        return await server.handle_klines(request)

    async def handle_time(self, server, request):
        return await server.handle_time(request)

    async def handle_ping(self, server, request):
        return await server.handle_ping(request)

    async def handle_exchange_info(self, server, request):
        return await server.handle_exchange_info(request)

    async def handle_websocket(self, server, request):
        return await server.handle_websocket(request)

    async def handle_boom(self, server, request):
        raise RuntimeError("kaboom")

    async def handle_limited(self, server, request):
        return web.json_response({"limited": True}, status=429)

    async def handle_limited_with_header(self, server, request):
        return web.json_response({"limited": True}, status=429, headers={"Retry-After": "99"})

    def format_rest_candles(self, candles, trading_pair, interval, tz_ms=0):
        return {
            "pair": trading_pair,
            "interval": interval,
            "tz_ms": tz_ms,
            "timestamps": [c.timestamp_ms for c in candles],
        }

    def format_ws_candle_message(self, candle, trading_pair, interval, is_final=False):
        return {"s": trading_pair, "i": interval, "c": candle.close, "x": is_final}

    def parse_ws_subscription(self, message):
        return [tuple(p) for p in message.get("params", [])]

    def create_ws_subscription_success(self, message, subscriptions):
        return {"result": None, "id": message.get("id"), "n": len(subscriptions)}

    def create_ws_subscription_key(self, trading_pair, interval):
        return f"{trading_pair}_{interval}"

    def parse_rest_candles_params(self, request):
        q = request.query
        if q.get("symbol") == "BAD":
            return {"valid": False, "error": {"msg": "bad params"}}
        return {
            "symbol": q.get("symbol"),
            "interval": q.get("interval"),
            "start_time": q.get("start_time"),
            "end_time": q.get("end_time"),
            "limit": int(q.get("limit", 500)),
            "timezone_offset_hours": float(q.get("tz", 0)),
        }

    def _interval_to_seconds(self, interval):
        return {"1m": 60, "5m": 300}.get(interval, 60)


def make_server() -> MockedExchangeServer:
    plugin = DelegatingPlugin(ExchangeType.BINANCE_SPOT, BinanceSpotAdapter)
    return MockedExchangeServer(plugin, "127.0.0.1", 0)


@pytest.fixture
def server():
    return make_server()


@pytest.fixture
def loaded_server(server):
    server.add_trading_pair("BTC-USDT", "1m", 50000.0)
    return server


@pytest.fixture
async def client(loaded_server):
    test_client = TestClient(TestServer(loaded_server.app))
    await test_client.start_server()
    yield test_client
    await test_client.close()


async def wait_until(predicate, attempts: int = 100) -> None:
    for _ in range(attempts):
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition not reached")


class TestConstruction:
    def test_default_ip_limits_derived_from_rest_limit(self, server):
        ip_limits = server.rate_limits["rest"]["ip_limits"]
        assert ip_limits == {"default": 100, "strict": 50}

    def test_existing_ip_limits_are_preserved(self):
        class WithIpLimits(DelegatingPlugin):
            @property
            def rate_limits(self):
                return {"rest": {"limit": 10, "period_ms": 1000, "ip_limits": {"x": 1}}}

        srv = MockedExchangeServer(WithIpLimits(ExchangeType.BINANCE_SPOT, BinanceSpotAdapter))
        assert srv.rate_limits["rest"]["ip_limits"] == {"x": 1}

    def test_exchange_name_keys_api_keys(self, server):
        assert list(server.api_keys) == ["binance"]
        assert "test_key" in server.api_keys["binance"]

    def test_routes_registered_and_unsupported_skipped(self, server):
        registered = {
            (r.method, r.resource.canonical)
            for r in server.app.router.routes()
            if r.method != "HEAD"
        }
        assert ("GET", "/klines") in registered
        assert ("POST", "/post") in registered
        assert ("PUT", "/put") in registered
        assert ("DELETE", "/delete") in registered
        assert ("GET", "/ws") in registered
        paths = {path for _, path in registered}
        assert not paths & {"/patch", "/missing", "/none", "/ws_missing", "/ws_none"}

    def test_unregistered_handlers_are_logged(self, monkeypatch):
        messages: list[str] = []
        monkeypatch.setattr(
            logging.Logger, "warning", lambda self, msg, *a, **k: messages.append(msg)
        )
        make_server()
        text = "\n".join(messages)
        assert "Unsupported method: PATCH for /patch" in text
        assert "Handler does_not_exist not found in plugin" in text
        assert "Handler null_handler not found in plugin" in text
        assert "WebSocket handler does_not_exist not found in plugin" in text
        assert "WebSocket handler null_handler not found in plugin" in text

    def test_url_unavailable_before_start(self, server):
        with pytest.raises(RuntimeError, match="Server not started"):
            _ = server.mocked_exchange_url


class TestTradingPairs:
    def test_add_pair_generates_trending_candles(self, loaded_server):
        candles = loaded_server.candles["BTC-USDT"]["1m"]
        assert len(candles) == 200
        assert loaded_server.trading_pairs["BTC-USDT"] == 50000.0
        assert loaded_server.last_candle_time["BTC-USDT"]["1m"] == candles[-1].timestamp * 1000

    def test_add_second_interval_keeps_existing_pair(self, loaded_server):
        loaded_server.add_trading_pair("BTC-USDT", "5m", 51000.0)
        assert set(loaded_server.candles["BTC-USDT"]) == {"1m", "5m"}
        assert loaded_server.trading_pairs["BTC-USDT"] == 51000.0

    def test_readding_same_interval_regenerates(self, loaded_server):
        before = loaded_server.candles["BTC-USDT"]["1m"]
        loaded_server.add_trading_pair("BTC-USDT", "1m", 50000.0)
        assert loaded_server.candles["BTC-USDT"]["1m"] is not before

    def test_small_count_uses_market_simulation(self, server):
        server.candles["BTC-USDT"] = {"1m": []}
        server.last_candle_time["BTC-USDT"] = {"1m": 0}
        server._generate_initial_candles("BTC-USDT", "1m", 100.0, num_candles=20)
        candles = server.candles["BTC-USDT"]["1m"]
        assert len(candles) == 20
        assert [b.timestamp - a.timestamp for a, b in zip(candles, candles[1:], strict=False)] == [
            60
        ] * 19

    def test_no_candles_leaves_last_time_untouched(self, server, monkeypatch):
        monkeypatch.setattr(
            CandleDataFactory, "create_trending_series", staticmethod(lambda **_: [])
        )
        server.candles["BTC-USDT"] = {"1m": []}
        server.last_candle_time["BTC-USDT"] = {"1m": 0}
        server._generate_initial_candles("BTC-USDT", "1m", 100.0)
        assert server.candles["BTC-USDT"]["1m"] == []
        assert server.last_candle_time["BTC-USDT"]["1m"] == 0

    def test_millisecond_candle_timestamp_not_rescaled(self, server, monkeypatch):
        fake = SimpleNamespace(timestamp=1_700_000_000_000)
        monkeypatch.setattr(
            CandleDataFactory, "create_trending_series", staticmethod(lambda **_: [fake])
        )
        server.candles["BTC-USDT"] = {"1m": []}
        server.last_candle_time["BTC-USDT"] = {"1m": 0}
        server._generate_initial_candles("BTC-USDT", "1m", 100.0)
        assert server.last_candle_time["BTC-USDT"]["1m"] == 1_700_000_000_000


class TestNetworkConditions:
    def test_set_network_conditions_clamps_rates(self, server):
        server.set_network_conditions(latency_ms=5, packet_loss_rate=2.0, error_rate=-1.0)
        assert (server.latency_ms, server.packet_loss_rate, server.error_rate) == (5, 1.0, 0.0)

    async def test_simulate_packet_loss_raises_timeout(self, server):
        server.set_network_conditions(packet_loss_rate=1.0)
        with pytest.raises(web.HTTPRequestTimeout):
            await server._simulate_network_conditions()

    @pytest.mark.parametrize(
        ("code", "exc"),
        [
            (500, web.HTTPInternalServerError),
            (502, web.HTTPBadGateway),
            (503, web.HTTPServiceUnavailable),
            (504, web.HTTPGatewayTimeout),
        ],
    )
    async def test_simulate_error_raises_matching_http_error(self, server, monkeypatch, code, exc):
        server.set_network_conditions(error_rate=1.0)
        monkeypatch.setattr(server_module.random, "choice", lambda _: code)
        with pytest.raises(exc):
            await server._simulate_network_conditions()

    async def test_simulate_latency_sleeps(self, server, monkeypatch):
        sleep = AsyncMock()
        monkeypatch.setattr(server_module.asyncio, "sleep", sleep)
        server.set_network_conditions(latency_ms=50)
        await server._simulate_network_conditions()
        sleep.assert_awaited_once_with(0.05)

    async def test_simulate_clean_conditions_is_noop(self, server):
        await server._simulate_network_conditions()

    async def test_wrapped_rest_packet_loss_returns_408(self, client, loaded_server):
        loaded_server.set_network_conditions(packet_loss_rate=1.0)
        resp = await client.get("/ping")
        assert resp.status == 408

    async def test_wrapped_rest_error_returns_json_error(self, client, loaded_server, monkeypatch):
        loaded_server.set_network_conditions(error_rate=1.0)
        monkeypatch.setattr(server_module.random, "choice", lambda options: options[2])
        resp = await client.get("/ping")
        assert resp.status == 503
        assert await resp.json() == {"code": 503, "msg": "Service unavailable"}

    async def test_wrapped_rest_latency_applies_delay(self, client, loaded_server, monkeypatch):
        sleep = AsyncMock()
        monkeypatch.setattr(server_module.asyncio, "sleep", sleep)
        loaded_server.set_network_conditions(latency_ms=7)
        resp = await client.get("/ping")
        assert resp.status == 200
        sleep.assert_any_await(0.007)

    async def test_wrapped_rest_handler_exception_returns_500(self, client):
        resp = await client.get("/boom")
        assert resp.status == 500
        body = await resp.json()
        assert body["code"] == -1000
        assert "kaboom" in body["msg"]

    async def test_wrapped_ws_handler_exception_returns_500(self, client):
        resp = await client.get("/ws_boom")
        assert resp.status == 500
        assert "kaboom" in await resp.text()

    async def test_wrapped_ws_latency_applies_delay(self, client, loaded_server):
        loaded_server.set_network_conditions(latency_ms=1)
        ws = await client.ws_connect("/ws")
        await ws.close()


class TestRateLimitResponses:
    def test_force_rate_limit_rejects_other_statuses(self, server):
        with pytest.raises(ValueError, match="418 or 429"):
            server.force_rate_limit_response(status=500)

    async def test_forced_418_with_retry_after(self, client, loaded_server):
        loaded_server.force_rate_limit_response(status=418, retry_after=3)
        resp = await client.get("/ping")
        assert resp.status == 418
        assert resp.headers["Retry-After"] == "3"
        assert await resp.json() == {"code": -1003, "msg": "IP banned"}

    async def test_forced_429_count_then_recovery(self, client, loaded_server):
        loaded_server.force_rate_limit_response(status=429, count=2)
        first = await client.get("/ping")
        second = await client.get("/ping")
        third = await client.get("/ping")
        assert (first.status, second.status, third.status) == (429, 429, 200)
        assert "Retry-After" not in first.headers
        assert (await first.json())["msg"] == "Too many requests"

    async def test_forced_response_skips_websocket_upgrade(self, client, loaded_server):
        loaded_server.force_rate_limit_response(status=429)
        ws = await client.ws_connect("/ws")
        await ws.close()
        assert len(loaded_server._forced_responses) == 1

    async def test_natural_429_gets_configured_retry_after(self, client, loaded_server):
        loaded_server.set_rate_limit_retry_after(2.5)
        resp = await client.get("/limited")
        assert resp.status == 429
        assert resp.headers["Retry-After"] == "2.5"

    async def test_natural_429_keeps_plugin_retry_after(self, client, loaded_server):
        loaded_server.set_rate_limit_retry_after(2.5)
        resp = await client.get("/limited_hdr")
        assert resp.headers["Retry-After"] == "99"

    async def test_natural_429_without_config_has_no_header(self, client):
        resp = await client.get("/limited")
        assert resp.status == 429
        assert "Retry-After" not in resp.headers

    @pytest.mark.parametrize("path", ["/klines", "/time", "/ping", "/info"])
    async def test_exhausted_rest_budget_returns_429(self, client, loaded_server, path):
        loaded_server.rate_limits["rest"]["limit"] = 0
        resp = await client.get(path, params={"symbol": "BTCUSDT", "interval": "1m"})
        assert resp.status == 429
        assert (await resp.json())["code"] == -1003


class TestCheckRateLimit:
    def test_rest_blocks_once_weight_limit_reached(self, server):
        server._time = lambda: NOW
        server.rate_limits["rest"]["limit"] = 2
        assert server._check_rate_limit("1.1.1.1")
        assert server._check_rate_limit("1.1.1.1")
        assert not server._check_rate_limit("1.1.1.1")
        assert server._check_rate_limit("2.2.2.2")

    def test_rest_window_expires_old_entries(self, server):
        server.rate_limits["rest"]["limit"] = 1
        server.rate_limits["rest"]["period_ms"] = 1000
        server._time = lambda: NOW
        assert server._check_rate_limit("1.1.1.1")
        assert not server._check_rate_limit("1.1.1.1")
        server._time = lambda: NOW + 2
        assert server._check_rate_limit("1.1.1.1")
        assert len(server.request_counts["rest"]["1.1.1.1"]["timestamps"]) == 1

    def test_ws_limit_and_expiry(self, server):
        server.rate_limits["ws"]["limit"] = 2
        server._time = lambda: NOW
        assert server._check_rate_limit("1.1.1.1", "ws")
        assert server._check_rate_limit("1.1.1.1", "ws")
        assert not server._check_rate_limit("1.1.1.1", "ws")
        server._time = lambda: NOW + 2
        assert server._check_rate_limit("1.1.1.1", "ws")

    def test_unknown_limit_type_is_allowed(self, server):
        assert server._check_rate_limit("1.1.1.1", "other")


class TestAuthentication:
    @staticmethod
    def req(key=None, remote="10.0.0.1"):
        headers = {"X-MBX-APIKEY": key} if key else {}
        return SimpleNamespace(headers=headers, remote=remote)

    def test_missing_key(self, server):
        result = server.verify_authentication(self.req())
        assert result["authenticated"] is False
        assert result["error"]["code"] == -2015

    def test_unknown_key(self, server):
        assert not server.verify_authentication(self.req("nope"))["authenticated"]

    def test_unknown_exchange(self, server):
        server.api_keys = {}
        assert not server.verify_authentication(self.req("test_key"))["authenticated"]

    def test_disabled_key(self, server):
        server.api_keys["binance"]["test_key"]["enabled"] = False
        assert not server.verify_authentication(self.req("test_key"))["authenticated"]

    def test_ip_whitelist(self, server):
        server.api_keys["binance"]["test_key"]["ip_whitelist"] = ["10.0.0.9"]
        assert not server.verify_authentication(self.req("test_key"))["authenticated"]
        assert server.verify_authentication(self.req("test_key", remote="10.0.0.9"))[
            "authenticated"
        ]

    def test_permissions(self, server):
        assert not server.verify_authentication(self.req("test_key"), ["WITHDRAW"])["authenticated"]
        ok = server.verify_authentication(self.req("test_key"), ["READ", "TRADE"])
        assert ok == {"authenticated": True, "error": None}

    def test_success_without_permissions(self, server):
        assert server.verify_authentication(self.req("test_key")) == {
            "authenticated": True,
            "error": None,
        }


class TestRestHandlers:
    async def test_klines_returns_limited_tail(self, client, loaded_server):
        expected = [c.timestamp_ms for c in loaded_server.candles["BTC-USDT"]["1m"][-5:]]
        resp = await client.get(
            "/klines", params={"symbol": "BTCUSDT", "interval": "1m", "limit": 5}
        )
        assert resp.status == 200
        body = await resp.json()
        assert body["pair"] == "BTC-USDT"
        assert body["timestamps"] == expected

    async def test_klines_time_window_and_timezone(self, client, loaded_server):
        candles = loaded_server.candles["BTC-USDT"]["1m"]
        start, end = candles[10].timestamp_ms, candles[20].timestamp_ms
        resp = await client.get(
            "/klines",
            params={
                "symbol": "BTCUSDT",
                "interval": "1m",
                "start_time": start,
                "end_time": end,
                "tz": 2,
            },
        )
        body = await resp.json()
        assert body["timestamps"] == [c.timestamp_ms for c in candles[10:21]]
        assert body["tz_ms"] == 7_200_000

    async def test_klines_zero_limit_returns_all(self, client):
        resp = await client.get(
            "/klines", params={"symbol": "BTCUSDT", "interval": "1m", "limit": 0}
        )
        assert len((await resp.json())["timestamps"]) == 200

    async def test_klines_invalid_params(self, client):
        resp = await client.get("/klines", params={"symbol": "BAD"})
        assert resp.status == 400
        assert await resp.json() == {"msg": "bad params"}

    async def test_klines_unknown_symbol(self, client):
        resp = await client.get("/klines", params={"symbol": "ETHUSDT", "interval": "1m"})
        assert resp.status == 400
        assert (await resp.json())["code"] == -1121

    async def test_klines_missing_symbol(self, client):
        resp = await client.get("/klines", params={"interval": "1m"})
        assert (await resp.json())["code"] == -1121

    async def test_klines_unknown_interval(self, client):
        resp = await client.get("/klines", params={"symbol": "BTCUSDT", "interval": "1d"})
        assert resp.status == 400
        assert (await resp.json())["code"] == -1120

    async def test_time_is_current_millis(self, client, loaded_server):
        loaded_server._time = lambda: NOW
        resp = await client.get("/time")
        assert await resp.json() == {"serverTime": int(NOW * 1000)}

    async def test_ping_and_non_get_methods(self, client):
        assert await (await client.get("/ping")).json() == {}
        assert (await client.post("/post")).status == 200
        assert (await client.put("/put")).status == 200
        assert (await client.delete("/delete")).status == 200

    async def test_exchange_info_describes_trading_pairs(self, client, loaded_server):
        loaded_server.trading_pairs["ETHUSDT"] = 3000.0  # no separator, known quote
        loaded_server.trading_pairs["FOOBAR"] = 1.0  # no separator, fallback split
        resp = await client.get("/info")
        body = await resp.json()
        by_symbol = {s["symbol"]: s for s in body["symbols"]}
        assert (by_symbol["BTCUSDT"]["baseAsset"], by_symbol["BTCUSDT"]["quoteAsset"]) == (
            "BTC",
            "USDT",
        )
        assert (by_symbol["ETHUSDT"]["baseAsset"], by_symbol["ETHUSDT"]["quoteAsset"]) == (
            "ETH",
            "USDT",
        )
        assert (by_symbol["FOOBAR"]["baseAsset"], by_symbol["FOOBAR"]["quoteAsset"]) == (
            "FOO",
            "BAR",
        )
        assert body["rateLimits"][0]["limit"] == loaded_server.rate_limits["rest"]["limit"]
        assert {f["filterType"] for f in body["exchangeFilters"]} == {
            "EXCHANGE_MAX_NUM_ORDERS",
            "EXCHANGE_MAX_NUM_ALGO_ORDERS",
        }


class TestWebSocket:
    @staticmethod
    def sub(pairs, method="SUBSCRIBE", msg_id=1):
        return {"method": method, "params": pairs, "id": msg_id}

    async def test_subscribe_sends_snapshot_then_ack(self, client, loaded_server):
        ws = await client.ws_connect("/ws")
        await ws.send_json(self.sub([["BTCUSDT", "1m"]], msg_id=7))
        snapshot = await ws.receive_json()
        ack = await ws.receive_json()
        last = loaded_server.candles["BTC-USDT"]["1m"][-1]
        assert snapshot == {"s": "BTC-USDT", "i": "1m", "c": last.close, "x": True}
        assert ack == {"result": None, "id": 7, "n": 1}
        assert len(loaded_server.subscriptions["BTC-USDT_1m"]) == 1
        await ws.close()

    async def test_subscribe_unknown_pair_acks_without_snapshot(self, client, loaded_server):
        ws = await client.ws_connect("/ws")
        await ws.send_json(self.sub([["XRPUSDT", "1m"]]))
        assert (await ws.receive_json())["n"] == 1
        assert "XRPUSDT_1m" in loaded_server.subscriptions
        await ws.close()

    async def test_list_subscriptions(self, client):
        ws = await client.ws_connect("/ws")
        await ws.send_json(self.sub([["BTCUSDT", "1m"]]))
        await ws.receive_json()
        await ws.receive_json()
        await ws.send_json({"method": "LIST_SUBSCRIPTIONS", "id": 9})
        assert await ws.receive_json() == {"result": ["BTC-USDT_1m"], "id": 9}
        await ws.close()

    async def test_push_candle_update_reaches_subscriber(self, client, loaded_server):
        ws = await client.ws_connect("/ws")
        await ws.send_json(self.sub([["BTCUSDT", "1m"]]))
        await ws.receive_json()
        await ws.receive_json()
        candle = loaded_server.candles["BTC-USDT"]["1m"][-2]
        await loaded_server._push_candle_update("BTC-USDT", "1m", candle, is_final=False)
        assert await ws.receive_json() == {
            "s": "BTC-USDT",
            "i": "1m",
            "c": candle.close,
            "x": False,
        }
        await ws.close()

    @staticmethod
    def stub_ws(remote="127.0.0.1"):
        """Stand-in exposing the ``request`` attribute the server's unsubscribe/cleanup read."""
        return StubWebSocket(SimpleNamespace(remote=remote))

    async def test_unsubscribe_removes_subscription(self, loaded_server):
        ws = self.stub_ws()
        loaded_server.subscriptions["BTC-USDT_1m"] = {ws}
        loaded_server.request_counts["ws"]["127.0.0.1"] = {
            "timestamps": deque(),
            "subscriptions": {"BTC-USDT_1m"},
        }
        data = self.sub([["BTCUSDT", "1m"]], method="UNSUBSCRIBE", msg_id=3)
        await loaded_server._handle_unsubscription(ws, data)
        ws.send_json.assert_awaited_once_with({"result": None, "id": 3, "n": 1})
        assert loaded_server.subscriptions == {}
        assert loaded_server.request_counts["ws"]["127.0.0.1"]["subscriptions"] == set()

    async def test_unsubscribe_keeps_other_subscribers(self, loaded_server):
        ws, other = self.stub_ws(), object()
        loaded_server.subscriptions["BTC-USDT_1m"] = {ws, other}
        await loaded_server._handle_unsubscription(ws, self.sub([["BTCUSDT", "1m"]]))
        assert loaded_server.subscriptions["BTC-USDT_1m"] == {other}

    async def test_unsubscribe_unknown_key_still_acks(self, loaded_server):
        ws = self.stub_ws("5.5.5.5")
        await loaded_server._handle_unsubscription(
            ws, self.sub([["NOPEUSDT", "1m"]], method="UNSUBSCRIBE", msg_id=4)
        )
        ws.send_json.assert_awaited_once_with({"result": None, "id": 4, "n": 1})

    async def test_subscription_limit_enforced(self, client, loaded_server):
        loaded_server.rate_limits["ws"]["subscription_limit"] = 0
        ws = await client.ws_connect("/ws")
        await ws.send_json(self.sub([["BTCUSDT", "1m"]], msg_id=5))
        assert await ws.receive_json() == {"error": "Subscription limit exceeded", "id": 5}
        assert loaded_server.subscriptions == {}
        await ws.close()

    async def test_unknown_method(self, client):
        ws = await client.ws_connect("/ws")
        await ws.send_json({"method": "WAT", "id": 2})
        assert await ws.receive_json() == {"error": "Unknown method: WAT", "id": 2}
        await ws.close()

    async def test_invalid_json(self, client):
        ws = await client.ws_connect("/ws")
        await ws.send_str("{not json")
        assert await ws.receive_json() == {"error": "Invalid JSON"}
        await ws.close()

    async def test_non_object_payload_reports_error(self, client):
        ws = await client.ws_connect("/ws")
        await ws.send_str("[]")
        assert (await ws.receive_json())["error"].startswith("Error: ")
        await ws.close()

    async def test_binary_frames_are_ignored(self, client):
        ws = await client.ws_connect("/ws")
        await ws.send_bytes(b"\x00\x01")
        await ws.send_json({"method": "LIST_SUBSCRIPTIONS", "id": 1})
        assert await ws.receive_json() == {"result": [], "id": 1}
        await ws.close()

    async def test_message_rate_limit(self, client, loaded_server):
        loaded_server.rate_limits["ws"]["limit"] = 2
        ws = await client.ws_connect("/ws")
        await ws.send_json({"method": "LIST_SUBSCRIPTIONS", "id": 1})
        assert (await ws.receive_json())["id"] == 1
        await ws.send_json({"method": "LIST_SUBSCRIPTIONS", "id": 2})
        assert await ws.receive_json() == {"error": "Rate limit exceeded"}
        await ws.close()

    async def test_connection_rate_limit_rejects_handshake(self, client, loaded_server):
        loaded_server.rate_limits["ws"]["limit"] = 0
        with pytest.raises(aiohttp.WSServerHandshakeError) as exc:
            await client.ws_connect("/ws")
        assert exc.value.status == 429

    async def test_disconnect_cleans_up_state(self, client, loaded_server):
        ws = await client.ws_connect("/ws")
        await ws.send_json(self.sub([["BTCUSDT", "1m"]]))
        await ws.receive_json()
        await ws.receive_json()
        assert len(loaded_server.ws_connections) == 1
        await ws.close()
        await wait_until(lambda: not loaded_server.ws_connections)
        assert loaded_server.subscriptions == {}

    def test_cleanup_resets_client_subscription_tracking(self, loaded_server):
        ws = self.stub_ws()
        loaded_server.ws_connections.add(ws)
        loaded_server.subscriptions = {"mine": {ws}, "shared": {ws, object()}}
        loaded_server.request_counts["ws"]["127.0.0.1"] = {
            "timestamps": deque(),
            "subscriptions": {"mine", "shared"},
        }
        loaded_server._cleanup_websocket(ws)
        assert loaded_server.ws_connections == set()
        assert set(loaded_server.subscriptions) == {"shared"}
        assert ws not in loaded_server.subscriptions["shared"]
        assert loaded_server.request_counts["ws"]["127.0.0.1"]["subscriptions"] == set()

    def test_cleanup_ignores_untracked_client(self, loaded_server):
        loaded_server._cleanup_websocket(self.stub_ws("9.9.9.9"))
        assert "9.9.9.9" not in loaded_server.request_counts["ws"]

    def test_get_subscriptions_for_connection(self, server):
        mine, other = object(), object()
        server.subscriptions = {"a": {mine}, "b": {other}, "c": {mine, other}}
        assert sorted(server._get_subscriptions_for_connection(mine)) == ["a", "c"]


class TestPushCandleUpdate:
    async def test_no_subscribers_is_noop(self, loaded_server):
        candle = loaded_server.candles["BTC-USDT"]["1m"][-1]
        await loaded_server._push_candle_update("BTC-USDT", "1m", candle)

    async def test_failed_and_closed_subscribers_are_dropped(self, loaded_server):
        candle = loaded_server.candles["BTC-USDT"]["1m"][-1]
        good = MagicMock(closed=False, send_json=AsyncMock())
        broken = MagicMock(closed=False, send_json=AsyncMock(side_effect=ConnectionError("x")))
        closed = MagicMock(closed=True, send_json=AsyncMock())
        subs = {good, broken, closed}
        loaded_server.subscriptions["BTC-USDT_1m"] = subs
        loaded_server.ws_connections.update(subs)

        await loaded_server._push_candle_update("BTC-USDT", "1m", candle, is_final=True)

        good.send_json.assert_awaited_once_with(
            {"s": "BTC-USDT", "i": "1m", "c": candle.close, "x": True}
        )
        closed.send_json.assert_not_awaited()
        assert loaded_server.subscriptions["BTC-USDT_1m"] == {good}
        assert loaded_server.ws_connections == {good}


class TestCandleGeneration:
    async def test_catches_up_to_current_time_and_pushes(self, server, monkeypatch):
        server._time = lambda: NOW
        server.add_trading_pair("BTC-USDT", "1m", 50000.0)
        server.candles["BTC-USDT"]["5m"] = []  # empty series is skipped
        subscriber = MagicMock(closed=False, send_json=AsyncMock())
        server.subscriptions["BTC-USDT_1m"] = {subscriber}
        server._time = lambda: NOW + 180

        monkeypatch.setattr(
            server_module.asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError)
        )
        with pytest.raises(asyncio.CancelledError):
            await server._generate_candles_periodically()

        candles = server.candles["BTC-USDT"]["1m"]
        assert len(candles) == 204
        assert candles[-1].timestamp == int(NOW) + 180
        assert server.last_candle_time["BTC-USDT"]["1m"] == (int(NOW) + 180) * 1000
        assert server.candles["BTC-USDT"]["5m"] == []
        assert subscriber.send_json.await_count == 4
        assert all(c.args[0]["x"] is True for c in subscriber.send_json.await_args_list)

    async def test_millisecond_tail_and_history_cap(self, server, monkeypatch):
        server._time = lambda: NOW + 180
        template = CandleDataFactory.create_random(timestamp=int(NOW), base_price=100.0)
        tail = SimpleNamespace(timestamp=int((NOW + 60) * 1000), close=100.0)
        server.candles["ETH-USDT"] = {"1m": [template] * 999 + [tail]}
        server.last_candle_time["ETH-USDT"] = {"1m": 0}
        server.trading_pairs["ETH-USDT"] = 100.0

        monkeypatch.setattr(
            server_module.asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError)
        )
        with pytest.raises(asyncio.CancelledError):
            await server._generate_candles_periodically()

        series = server.candles["ETH-USDT"]["1m"]
        assert len(series) == 1000
        assert [c.timestamp for c in series[-2:]] == [int(NOW) + 120, int(NOW) + 180]
        assert server.last_candle_time["ETH-USDT"]["1m"] == (int(NOW) + 180) * 1000


class TestLifecycle:
    async def test_start_serves_requests_and_stop_closes_everything(self, loaded_server):
        url = await loaded_server.start()
        assert url == "http://127.0.0.1:0"
        assert loaded_server.mocked_exchange_url == url
        assert len(loaded_server._tasks) == 1

        port = loaded_server.runner.addresses[0][1]
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/ping") as resp:
                assert resp.status == 200
            ws = await session.ws_connect(f"http://127.0.0.1:{port}/ws")
            await wait_until(lambda: loaded_server.ws_connections)

            done_task = asyncio.create_task(asyncio.sleep(0))
            await done_task
            loaded_server._tasks.append(done_task)
            loaded_server.ws_connections.add(MagicMock(closed=True))

            await loaded_server.stop()

            msg = await ws.receive()
            assert msg.type in (
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSING,
                aiohttp.WSMsgType.CLOSED,
            )
            assert ws.closed

        assert loaded_server._tasks == []
        assert loaded_server.ws_connections == set()
        assert loaded_server.subscriptions == {}

    async def test_stop_before_start_is_safe(self, server):
        await server.stop()
