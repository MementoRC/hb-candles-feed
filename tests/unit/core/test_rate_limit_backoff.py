"""
Tests for the HTTP 429 / 418 pool-wide backoff (#93 follow-up).

Timing uses a fake clock except where a real, short (<= 0.3s) pause proves the deadline
is not tied to an event loop.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from candles_feed.adapters.adapter_mixins import SyncOnlyAdapter
from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.protocols import PausableRateLimiterProtocol, RestRateLimiterProtocol
from candles_feed.core.rate_limiter import (
    DEFAULT_418_BAN_SECONDS,
    DEFAULT_429_BACKOFF_BASE_SECONDS,
    DEFAULT_429_BACKOFF_CAP_SECONDS,
    AsyncRateLimiter,
    BackoffPolicy,
    RateLimitedNetworkClient,
    RateLimitExceededError,
    RestRateLimit,
    get_rate_limiter,
    parse_retry_after,
    reset_rate_limiters,
    set_adapter_rate_limiter,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_rate_limiters()
    yield
    reset_rate_limiters()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def make_limiter(clock: FakeClock, max_requests: int = 100) -> AsyncRateLimiter:
    return AsyncRateLimiter(RestRateLimit(max_requests, 1.0), clock=clock, sleep=clock.sleep)


class TestParseRetryAfter:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("7", 7.0), (" 2.5 ", 2.5), ("0", 0.0), ("-3", 0.0)],
    )
    def test_delta_seconds(self, value, expected):
        assert parse_retry_after(value) == expected

    @pytest.mark.parametrize("value", [None, "", "  ", "soon", "nan", "inf", "Mon, 99 Foo"])
    def test_garbage_is_none(self, value):
        assert parse_retry_after(value) is None

    def test_http_date_in_future(self):
        when = datetime.now(UTC) + timedelta(seconds=30)
        result = parse_retry_after(format_datetime(when, usegmt=True))
        assert result is not None
        assert 27 <= result <= 31

    def test_http_date_in_past_is_zero(self):
        when = datetime.now(UTC) - timedelta(seconds=30)
        assert parse_retry_after(format_datetime(when, usegmt=True)) == 0.0


class TestRateLimitExceededError:
    def test_from_response_is_case_insensitive(self):
        err = RateLimitExceededError.from_response(429, {"retry-after": "4"})
        assert (err.status, err.retry_after) == (429, 4.0)

    def test_from_response_without_headers(self):
        assert RateLimitExceededError.from_response(418, None).retry_after is None


class TestBackoffPolicy:
    def test_exponential_429_with_cap(self):
        policy = BackoffPolicy()
        delays = [policy.next_delay(429, None) for _ in range(10)]
        base = DEFAULT_429_BACKOFF_BASE_SECONDS
        assert delays[:4] == [base, 2 * base, 4 * base, 8 * base]
        assert max(delays) == DEFAULT_429_BACKOFF_CAP_SECONDS
        assert delays[-1] == DEFAULT_429_BACKOFF_CAP_SECONDS

    def test_reset_restarts_streak(self):
        policy = BackoffPolicy()
        policy.next_delay(429, None)
        policy.next_delay(429, None)
        policy.reset()
        assert policy.next_delay(429, None) == DEFAULT_429_BACKOFF_BASE_SECONDS

    def test_418_uses_ban_default(self):
        assert BackoffPolicy().next_delay(418, None) == DEFAULT_418_BAN_SECONDS

    def test_retry_after_wins(self):
        policy = BackoffPolicy()
        assert policy.next_delay(429, 1.5) == 1.5
        assert policy.next_delay(418, 0.0) == 0.0


class TestAsyncRateLimiterPause:
    def test_satisfies_protocols(self, clock):
        limiter = make_limiter(clock)
        assert isinstance(limiter, RestRateLimiterProtocol)
        assert isinstance(limiter, PausableRateLimiterProtocol)

    async def test_pause_blocks_acquire_for_all_feeds_of_a_pool(self, clock):
        feed_a = get_rate_limiter("pool", RestRateLimit(100, 1.0), clock=clock, sleep=clock.sleep)
        feed_b = get_rate_limiter("pool", RestRateLimit(100, 1.0), clock=clock, sleep=clock.sleep)
        assert feed_a is feed_b

        feed_a.pause(5.0)
        await feed_b.acquire()

        assert clock.sleeps == [pytest.approx(5.0)]

    async def test_no_wait_after_pause_elapsed(self, clock):
        limiter = make_limiter(clock)
        limiter.pause(2.0)
        clock.now += 3.0
        await limiter.acquire()
        assert clock.sleeps == []

    async def test_pause_never_shortens(self, clock):
        limiter = make_limiter(clock)
        limiter.pause(10.0)
        limiter.pause(1.0)
        await limiter.acquire()
        assert clock.sleeps == [pytest.approx(10.0)]

    async def test_pause_extended_while_waiting_is_honoured(self, clock):
        extended = False

        async def sleep(seconds: float) -> None:
            nonlocal extended
            clock.sleeps.append(seconds)
            clock.now += seconds
            if not extended:
                extended = True
                limiter.pause(3.0)  # another feed got a 429 during our wait

        limiter = AsyncRateLimiter(RestRateLimit(100, 1.0), clock=clock, sleep=sleep)
        limiter.pause(2.0)
        await limiter.acquire()
        assert clock.sleeps == [pytest.approx(2.0), pytest.approx(3.0)]

    async def test_pause_arriving_during_window_wait_is_honoured(self, clock):
        paused = False

        async def sleep(seconds: float) -> None:
            nonlocal paused
            clock.sleeps.append(seconds)
            clock.now += seconds
            if not paused:
                paused = True
                limiter.pause(4.0)

        limiter = AsyncRateLimiter(RestRateLimit(1, 1.0), clock=clock, sleep=sleep)
        await limiter.acquire()  # fills the 1-per-second window
        await limiter.acquire()
        assert clock.sleeps == [pytest.approx(1.0), pytest.approx(4.0)]

    async def test_deadline_is_shared_across_event_loops(self):
        limiter = AsyncRateLimiter(RestRateLimit(100, 1.0))
        limiter.pause(0.2)
        started = time.monotonic()

        await asyncio.to_thread(lambda: asyncio.run(limiter.acquire()))  # a different loop

        assert time.monotonic() - started >= 0.18


class FailingClient:
    def __init__(self, error: Exception | None = None, result: object = "ok") -> None:
        self.error = error
        self.result = result
        self.calls = 0

    async def get_rest_data(self, *args, **kwargs):
        self.calls += 1
        await asyncio.sleep(0)  # in flight: lets concurrent callers all pass acquire first
        if self.error is not None:
            raise self.error
        return self.result


class TestRateLimitedNetworkClientBackoff:
    async def test_pauses_pool_logs_once_and_reraises(self, clock, caplog):
        limiter = make_limiter(clock)
        inner = FailingClient(RateLimitExceededError(status=429, retry_after=7.0))
        client = RateLimitedNetworkClient(inner, limiter)

        with caplog.at_level(logging.WARNING), pytest.raises(RateLimitExceededError):
            await client.get_rest_data(url="http://x")

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "429" in warnings[0].getMessage()
        assert "7.0" in warnings[0].getMessage()
        await limiter.acquire()  # another feed on the pool now waits
        assert clock.sleeps == [pytest.approx(7.0)]

    async def test_streak_grows_then_resets_on_success(self, clock):
        limiter = make_limiter(clock)
        inner = FailingClient(RateLimitExceededError(status=429))
        client = RateLimitedNetworkClient(inner, limiter)

        for expected in (5.0, 10.0):
            with pytest.raises(RateLimitExceededError):
                await client.get_rest_data()
            before = clock.now
            await limiter.acquire()
            assert clock.now - before == pytest.approx(expected, abs=0.01)

        inner.error = None
        await client.get_rest_data()
        assert limiter.backoff.streak == 0

        inner.error = RateLimitExceededError(status=429)
        with pytest.raises(RateLimitExceededError):
            await client.get_rest_data()
        before = clock.now
        await limiter.acquire()
        assert clock.now - before == pytest.approx(5.0, abs=0.01)

    async def test_other_errors_do_not_pause_or_reset(self, clock):
        limiter = make_limiter(clock)
        limiter.backoff.streak = 2
        client = RateLimitedNetworkClient(FailingClient(RuntimeError("boom")), limiter)

        with pytest.raises(RuntimeError):
            await client.get_rest_data()
        await limiter.acquire()

        assert clock.sleeps == []
        assert limiter.backoff.streak == 2

    async def test_non_pausable_limiter_warns_once_and_reraises(self, caplog):
        class AcquireOnly:
            async def acquire(self) -> None:
                return None

        limiter = AcquireOnly()
        client = RateLimitedNetworkClient(
            FailingClient(RateLimitExceededError(status=429)), limiter
        )

        with caplog.at_level(logging.WARNING):
            for _ in range(3):
                with pytest.raises(RateLimitExceededError):
                    await client.get_rest_data()

        assert len([r for r in caplog.records if "cannot pause" in r.getMessage()]) == 1


class TestSyncPaths:
    async def test_sync_only_adapter_pauses_pool(self, clock):
        class Adapter(SyncOnlyAdapter):
            def fetch_rest_candles_synchronous(self, trading_pair, interval, start_time, limit):
                raise RateLimitExceededError(status=418, retry_after=None)

        adapter = Adapter()
        limiter = make_limiter(clock)
        set_adapter_rate_limiter(adapter, limiter)

        with pytest.raises(RateLimitExceededError):
            await adapter.fetch_rest_candles("BTC-USDT", "1m")
        await limiter.acquire()

        assert clock.sleeps == [pytest.approx(DEFAULT_418_BAN_SECONDS)]

    async def test_sync_only_adapter_success_resets_streak(self, clock):
        class Adapter(SyncOnlyAdapter):
            def fetch_rest_candles_synchronous(self, trading_pair, interval, start_time, limit):
                return []

        adapter = Adapter()
        limiter = make_limiter(clock)
        limiter.backoff.streak = 3
        set_adapter_rate_limiter(adapter, limiter)

        assert await adapter.fetch_rest_candles("BTC-USDT", "1m") == []
        assert limiter.backoff.streak == 0


@pytest.fixture
async def status_server():
    async def too_many(request: web.Request) -> web.Response:
        return web.json_response({}, status=429, headers={"Retry-After": "7"})

    async def banned(request: web.Request) -> web.Response:
        return web.json_response({}, status=418)

    async def broken(request: web.Request) -> web.Response:
        return web.json_response({}, status=500)

    app = web.Application()
    app.router.add_get("/429", too_many)
    app.router.add_get("/418", banned)
    app.router.add_get("/500", broken)
    server = TestServer(app)
    await server.start_server()
    yield server
    await server.close()


class TestNetworkClientTranslation:
    async def test_429_with_retry_after(self, status_server):
        async with NetworkClient() as client:
            with pytest.raises(RateLimitExceededError) as excinfo:
                await client.get_rest_data(str(status_server.make_url("/429")))

        assert (excinfo.value.status, excinfo.value.retry_after) == (429, 7.0)
        assert isinstance(excinfo.value.__cause__, aiohttp.ClientResponseError)

    async def test_418_without_retry_after(self, status_server):
        async with NetworkClient() as client:
            with pytest.raises(RateLimitExceededError) as excinfo:
                await client.get_rest_data(str(status_server.make_url("/418")))

        assert (excinfo.value.status, excinfo.value.retry_after) == (418, None)

    async def test_other_errors_unchanged(self, status_server):
        async with NetworkClient() as client:
            with pytest.raises(aiohttp.ClientResponseError) as excinfo:
                await client.get_rest_data(str(status_server.make_url("/500")))

        assert excinfo.value.status == 500


class TestHummingbotNetworkClientTranslation:
    """Uses the mock web assistant, whose ``call`` has upstream's ``(request, timeout)`` shape."""

    @pytest.fixture
    def client_and_connection(self):
        from unittest.mock import patch

        from candles_feed.hb_compat.hummingbot_network_client_adapter import (
            HummingbotNetworkClient,
        )
        from candles_feed.mocking_resources.hummingbot.mock_components import (
            create_mock_hummingbot_components,
        )

        components = create_mock_hummingbot_components(
            rest_responses={"https://x/ok": {"a": 1}, "https://x/limited": {}, "https://x/err": {}}
        )
        with patch(
            "candles_feed.hb_compat.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True
        ):
            client = HummingbotNetworkClient(
                throttler=components["throttler"],
                web_assistants_factory=components["web_assistants_factory"],
            )
        return client, components["web_assistants_factory"].rest_connection

    async def test_ok_uses_request_shape(self, client_and_connection):
        client, connection = client_and_connection
        assert await client.get_rest_data("https://x/ok", params={"p": 1, "q": None}) == {"a": 1}
        assert connection.requests[0]["url"] == "https://x/ok"
        assert connection.requests[0]["params"] == {"p": 1}

    async def test_429_translated_with_retry_after(self, client_and_connection):
        client, connection = client_and_connection
        connection.set_error("https://x/limited", 429, {"Retry-After": "3"})

        with pytest.raises(RateLimitExceededError) as excinfo:
            await client.get_rest_data("https://x/limited")

        assert (excinfo.value.status, excinfo.value.retry_after) == (429, 3.0)

    async def test_418_translated(self, client_and_connection):
        client, connection = client_and_connection
        connection.set_error("https://x/limited", 418)

        with pytest.raises(RateLimitExceededError) as excinfo:
            await client.get_rest_data("https://x/limited")

        assert excinfo.value.status == 418

    async def test_other_http_error_raises_oserror(self, client_and_connection):
        client, connection = client_and_connection
        connection.set_error("https://x/err", 503)

        with pytest.raises(OSError, match="503"):
            await client.get_rest_data("https://x/err")


class TestCcxtTranslation:
    @pytest.mark.parametrize("name", ["RateLimitExceeded", "DDoSProtection"])
    def test_ccxt_rate_limit_errors_are_translated(self, name):
        ccxt = pytest.importorskip("ccxt")
        from candles_feed.adapters.ccxt.ccxt_base_adapter import CCXTBaseAdapter

        fake_self = SimpleNamespace(
            exchange=MagicMock(fetch_ohlcv=MagicMock(side_effect=getattr(ccxt, name)("slow down"))),
            _get_rest_params=lambda *a, **k: {
                "symbol": "BTC/USDT",
                "timeframe": "1m",
                "since": None,
                "limit": 5,
            },
        )

        with pytest.raises(RateLimitExceededError) as excinfo:
            CCXTBaseAdapter.fetch_rest_candles_synchronous(fake_self, "BTC-USDT", "1m")

        assert (excinfo.value.status, excinfo.value.retry_after) == (429, None)
        assert isinstance(excinfo.value.__cause__, getattr(ccxt, name))


class TestThrottlerBridgePause:
    @pytest.fixture
    def bridges(self):
        pytest.importorskip("hummingbot")
        from hummingbot.core.api_throttler.async_throttler import AsyncThrottler

        from candles_feed.hb_compat.throttler_bridge import ConnectorThrottlerBridge

        throttler = AsyncThrottler([])
        return (
            throttler,
            ConnectorThrottlerBridge(throttler, BinanceSpotAdapter),
            ConnectorThrottlerBridge(throttler, BinanceSpotAdapter),
        )

    async def test_pause_is_shared_between_bridges(self, bridges):
        _, first, second = bridges
        assert isinstance(first, PausableRateLimiterProtocol)
        assert first.backoff is second.backoff

        first.pause(0.2)
        started = time.monotonic()
        await second.acquire()

        assert time.monotonic() - started >= 0.18

    async def test_other_throttler_is_unaffected(self, bridges):
        from hummingbot.core.api_throttler.async_throttler import AsyncThrottler

        from candles_feed.hb_compat.throttler_bridge import ConnectorThrottlerBridge

        _, first, _ = bridges
        other = ConnectorThrottlerBridge(AsyncThrottler([]), BinanceSpotAdapter)
        first.pause(30.0)

        await asyncio.wait_for(other.acquire(), timeout=2.0)

    async def test_rate_limited_client_pauses_bridge(self, bridges):
        _, first, second = bridges
        client = RateLimitedNetworkClient(
            FailingClient(RateLimitExceededError(status=429, retry_after=0.2)), first
        )

        with pytest.raises(RateLimitExceededError):
            await client.get_rest_data()
        started = time.monotonic()
        await second.acquire()

        assert time.monotonic() - started >= 0.18


class TestBurstHandling:
    async def test_concurrent_429_burst_is_one_pause(self, clock):
        limiter = make_limiter(clock)
        client = RateLimitedNetworkClient(
            FailingClient(RateLimitExceededError(status=429)), limiter
        )

        results = await asyncio.gather(
            *(client.get_rest_data() for _ in range(5)), return_exceptions=True
        )

        assert all(isinstance(r, RateLimitExceededError) for r in results)
        assert limiter.backoff.streak == 1
        before = clock.now
        await limiter.acquire()
        assert clock.now - before == pytest.approx(DEFAULT_429_BACKOFF_BASE_SECONDS, abs=0.01)

        # After the pause expired, the next 429 is a new event: 10s.
        with pytest.raises(RateLimitExceededError):
            await client.get_rest_data()
        before = clock.now
        await limiter.acquire()
        assert clock.now - before == pytest.approx(2 * DEFAULT_429_BACKOFF_BASE_SECONDS, abs=0.01)

    async def test_retry_after_and_418_still_extend_an_active_pause(self, clock):
        limiter = make_limiter(clock)
        limiter.pause(5.0)
        limiter_client = RateLimitedNetworkClient(
            FailingClient(RateLimitExceededError(status=429, retry_after=20.0)), limiter
        )
        with pytest.raises(RateLimitExceededError):
            await limiter_client.get_rest_data()
        limiter_client = RateLimitedNetworkClient(
            FailingClient(RateLimitExceededError(status=418)), limiter
        )
        with pytest.raises(RateLimitExceededError):
            await limiter_client.get_rest_data()

        before = clock.now
        await limiter.acquire()
        assert clock.now - before == pytest.approx(DEFAULT_418_BAN_SECONDS, abs=0.01)
