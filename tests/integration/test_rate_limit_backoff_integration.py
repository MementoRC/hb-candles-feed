"""
Integration tests for the HTTP 429 / 418 backoff against real servers.

Covers the mock exchange server (real ~1s Retry-After delay) and hummingbot's real
``RESTAssistant`` / ``WebAssistantsFactory`` / ``AsyncThrottler`` via
``HummingbotNetworkClient``.
"""

import json
import sys
import time

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from candles_feed.core.network_client import NetworkClient
from candles_feed.core.rate_limiter import (
    RateLimitedNetworkClient,
    RateLimitExceededError,
    RestRateLimit,
    get_rate_limiter,
    reset_rate_limiters,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_rate_limiters()
    yield
    reset_rate_limiters()


@pytest.mark.integration
class TestMockServerBackoffIntegration:
    @pytest.fixture
    async def server(self):
        from candles_feed.mocking_resources.core.server import MockedExchangeServer
        from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import (
            BinanceSpotPlugin,
        )

        server = MockedExchangeServer(BinanceSpotPlugin(), "127.0.0.1", 8793)
        server.add_trading_pair("BTCUSDT", "1m", 50000.0)
        server.url = await server.start()
        yield server
        await server.stop()

    async def test_forced_429_delays_second_feed_on_same_pool(self, server):
        server.force_rate_limit_response(429, retry_after=1, count=1)
        url = f"{server.url}/api/v3/klines"
        params = {"symbol": "BTCUSDT", "interval": "1m", "limit": 2}
        limiter = get_rate_limiter("mock-pool", RestRateLimit(100, 1.0))

        async with NetworkClient() as raw_a, NetworkClient() as raw_b:
            feed_a = RateLimitedNetworkClient(raw_a, limiter)
            feed_b = RateLimitedNetworkClient(raw_b, limiter)

            with pytest.raises(RateLimitExceededError) as excinfo:
                await feed_a.get_rest_data(url, params=params)
            assert excinfo.value.retry_after == 1.0

            started = time.monotonic()
            data = await feed_b.get_rest_data(url, params=params)

        assert time.monotonic() - started >= 0.95
        assert data

    async def test_forced_418_has_status_and_optional_retry_after(self, server):
        server.force_rate_limit_response(418, retry_after=None)
        async with NetworkClient() as raw:
            with pytest.raises(RateLimitExceededError) as excinfo:
                await raw.get_rest_data(f"{server.url}/api/v3/time")

        assert (excinfo.value.status, excinfo.value.retry_after) == (418, None)

    async def test_natural_429_carries_configured_retry_after(self, server):
        server.set_rate_limit_retry_after(2)
        server.rate_limits["rest"]["limit"] = 0
        async with NetworkClient() as raw:
            with pytest.raises(RateLimitExceededError) as excinfo:
                await raw.get_rest_data(f"{server.url}/api/v3/time")

        assert (excinfo.value.status, excinfo.value.retry_after) == (429, 2.0)


@pytest.mark.integration
class TestRealRestAssistant:
    """HummingbotNetworkClient on upstream's real RESTAssistant (needs hummingbot importable)."""

    @pytest.fixture
    async def server(self):
        async def ok(request: web.Request) -> web.Response:
            return web.json_response([[1, 2, 3]])

        async def limited(request: web.Request) -> web.Response:
            return web.json_response({}, status=429, headers={"Retry-After": "7"})

        async def banned(request: web.Request) -> web.Response:
            return web.json_response({}, status=418, headers={"Retry-After": "11"})

        async def broken(request: web.Request) -> web.Response:
            return web.json_response({"oops": 1}, status=500)

        app = web.Application()
        app.router.add_get("/ok", ok)
        app.router.add_get("/429", limited)
        app.router.add_get("/418", banned)
        app.router.add_get("/500", broken)
        server = TestServer(app)
        await server.start_server()
        yield server
        await server.close()

    @pytest.fixture
    async def client(self, monkeypatch):
        pytest.importorskip("hummingbot")
        try:
            import ujson  # noqa: F401
        except ImportError:  # upstream only uses ujson.dumps; json is a drop-in here
            monkeypatch.setitem(sys.modules, "ujson", json)
        monkeypatch.setattr(
            "candles_feed.hb_compat.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True
        )
        from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
        from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory

        from candles_feed.hb_compat.hummingbot_network_client_adapter import (
            HummingbotNetworkClient,
        )

        throttler = AsyncThrottler([])
        factory = WebAssistantsFactory(throttler=throttler)
        client = HummingbotNetworkClient(throttler=throttler, web_assistants_factory=factory)
        async with client:
            yield client

    async def test_200_returns_json(self, client, server):
        data = await client.get_rest_data(str(server.make_url("/ok")), params={"a": 1, "b": None})
        assert data == [[1, 2, 3]]

    @pytest.mark.parametrize(
        ("path", "status", "retry_after"), [("429", 429, 7.0), ("418", 418, 11.0)]
    )
    async def test_rate_limit_statuses(self, client, server, path, status, retry_after):
        with pytest.raises(RateLimitExceededError) as excinfo:
            await client.get_rest_data(str(server.make_url(f"/{path}")))

        assert (excinfo.value.status, excinfo.value.retry_after) == (status, retry_after)

    async def test_500_raises_oserror_with_status(self, client, server):
        with pytest.raises(OSError, match="500"):
            await client.get_rest_data(str(server.make_url("/500")))
