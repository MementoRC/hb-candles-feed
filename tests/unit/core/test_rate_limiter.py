"""
Tests for framework-level REST rate limiting (#93).

All timing uses a fake clock; nothing here really sleeps.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.rate_limiter import (
    AsyncRateLimiter,
    RateLimitedNetworkClient,
    RateLimitPoolConflictError,
    RestRateLimit,
    get_adapter_rate_limiter,
    get_rate_limiter,
    pool_key_for,
    reset_rate_limiters,
)


class FakeClock:
    """Deterministic clock whose sleep just advances time."""

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


def make_limiter(clock: FakeClock, max_requests: int = 3, period: float = 1.0) -> AsyncRateLimiter:
    return AsyncRateLimiter(RestRateLimit(max_requests, period), clock=clock, sleep=clock.sleep)


class TestRestRateLimit:
    def test_is_frozen(self):
        limit = RestRateLimit(5, 1.0)
        with pytest.raises(AttributeError):
            limit.max_requests = 10  # type: ignore[misc]

    def test_base_adapter_has_conservative_default(self):
        assert RestRateLimit(5, 1.0) == BaseAdapter.REST_RATE_LIMIT

    @pytest.mark.parametrize("period", [float("nan"), float("inf"), float("-inf"), 0, -1.0])
    def test_rejects_non_finite_or_non_positive_period(self, period):
        with pytest.raises(ValueError):
            RestRateLimit(1, period)


class TestAsyncRateLimiter:
    async def test_calls_within_budget_do_not_wait(self, clock):
        limiter = make_limiter(clock, max_requests=3)
        for _ in range(3):
            await limiter.acquire()
        assert clock.sleeps == []

    async def test_n_plus_one_call_waits_for_window(self, clock):
        limiter = make_limiter(clock, max_requests=3, period=1.0)
        start = clock.now
        for _ in range(4):
            await limiter.acquire()
        assert len(clock.sleeps) == 1
        assert clock.now - start == pytest.approx(1.0)

    async def test_pacing_over_many_calls(self, clock):
        limiter = make_limiter(clock, max_requests=2, period=1.0)
        start = clock.now
        admitted: list[float] = []
        for _ in range(6):
            await limiter.acquire()
            admitted.append(clock.now - start)
        # 2 per second: admissions at 0, 0, 1, 1, 2, 2 (no burst-then-long-wait)
        assert admitted == [pytest.approx(t) for t in (0.0, 0.0, 1.0, 1.0, 2.0, 2.0)]

    async def test_window_expiry_frees_budget(self, clock):
        limiter = make_limiter(clock, max_requests=2, period=1.0)
        await limiter.acquire()
        await limiter.acquire()
        clock.now += 1.5
        await limiter.acquire()
        assert clock.sleeps == []


class TestLockPerEventLoop:
    def test_limiter_usable_across_event_loops(self):
        clock = FakeClock()

        async def yielding_sleep(seconds: float) -> None:
            await asyncio.sleep(0)
            clock.now += seconds

        limiter = AsyncRateLimiter(RestRateLimit(1, 1.0), clock=clock, sleep=yielding_sleep)

        async def contend() -> None:
            # Three waiters on a budget of one force real lock contention.
            await asyncio.gather(*(limiter.acquire() for _ in range(3)))

        asyncio.run(contend())
        asyncio.run(contend())


class TestPools:
    async def test_independent_pools_do_not_block_each_other(self, clock):
        limit = RestRateLimit(1, 10.0)
        a = get_rate_limiter("pool-a", limit, clock=clock, sleep=clock.sleep)
        b = get_rate_limiter("pool-b", limit, clock=clock, sleep=clock.sleep)
        await a.acquire()
        await b.acquire()
        assert clock.sleeps == []
        await a.acquire()
        assert clock.sleeps == [pytest.approx(10.0)]

    def test_same_pool_key_returns_same_limiter(self):
        limit = RestRateLimit(1, 1.0)
        assert get_rate_limiter("shared", limit) is get_rate_limiter("shared", limit)

    def test_differing_limit_on_existing_pool_raises(self):
        get_rate_limiter("shared", RestRateLimit(1, 1.0), owner="pkg.SpotAdapter")
        with pytest.raises(RateLimitPoolConflictError) as excinfo:
            get_rate_limiter("shared", RestRateLimit(2, 1.0), owner="pkg.PerpAdapter")
        message = str(excinfo.value)
        assert "'shared'" in message
        assert "pkg.SpotAdapter" in message
        assert "pkg.PerpAdapter" in message
        assert "max_requests=1" in message
        assert "max_requests=2" in message
        assert isinstance(excinfo.value, ValueError)

    def test_differing_period_raises(self):
        get_rate_limiter("shared", RestRateLimit(1, 1.0))
        with pytest.raises(RateLimitPoolConflictError):
            get_rate_limiter("shared", RestRateLimit(1, 2.0))

    def test_differing_clock_with_same_limit_is_not_a_conflict(self, clock):
        first = get_rate_limiter("shared", RestRateLimit(1, 1.0))
        assert get_rate_limiter("shared", RestRateLimit(1, 1.0), clock=clock) is first

    def test_adapters_with_conflicting_pool_limits_raise(self):
        class SpotAdapter(BaseAdapter):
            REST_RATE_LIMIT = RestRateLimit(1, 1.0)
            REST_RATE_LIMIT_POOL = "conflict-pool"

        class PerpAdapter(BaseAdapter):
            REST_RATE_LIMIT = RestRateLimit(2, 1.0)
            REST_RATE_LIMIT_POOL = "conflict-pool"

        get_adapter_rate_limiter(SpotAdapter)
        with pytest.raises(RateLimitPoolConflictError, match="SpotAdapter"):
            get_adapter_rate_limiter(PerpAdapter)

    def test_pool_key_defaults_to_adapter_class(self):
        class AdapterA(BaseAdapter):
            pass

        class AdapterB(BaseAdapter):
            pass

        class Shared(BaseAdapter):
            REST_RATE_LIMIT_POOL = "exchange-x"

        class Shared2(BaseAdapter):
            REST_RATE_LIMIT_POOL = "exchange-x"

        assert pool_key_for(AdapterA) != pool_key_for(AdapterB)
        assert pool_key_for(AdapterA) == pool_key_for(AdapterA)
        assert pool_key_for(Shared) == pool_key_for(Shared2) == "exchange-x"

    def test_pool_key_works_on_instances(self):
        class Plain:
            REST_RATE_LIMIT_POOL = None

        assert pool_key_for(Plain()) == pool_key_for(Plain)


class TestRateLimitedNetworkClient:
    async def test_get_rest_data_acquires_then_delegates(self, clock):
        calls: list[str] = []
        inner = MagicMock()

        async def fake_get(*args, **kwargs):
            calls.append("delegate")
            return {"ok": True}

        inner.get_rest_data = AsyncMock(side_effect=fake_get)
        limiter = make_limiter(clock, max_requests=1, period=2.0)
        real_acquire = limiter.acquire

        async def recording_acquire() -> None:
            calls.append("acquire")
            await real_acquire()

        limiter.acquire = recording_acquire  # type: ignore[method-assign]
        client = RateLimitedNetworkClient(inner, limiter)

        assert await client.get_rest_data(url="http://x", params={"a": 1}) == {"ok": True}
        assert calls == ["acquire", "delegate"]
        await client.get_rest_data(url="http://x")
        assert calls == ["acquire", "delegate", "acquire", "delegate"]

        assert inner.get_rest_data.await_count == 2
        inner.get_rest_data.assert_any_await(url="http://x", params={"a": 1})
        assert clock.sleeps == [pytest.approx(2.0)]

    async def test_other_attributes_delegate(self, clock):
        inner = MagicMock()
        inner.establish_ws_connection = AsyncMock(return_value="ws")
        client = RateLimitedNetworkClient(inner, make_limiter(clock))
        assert await client.establish_ws_connection("wss://x") == "ws"

    async def test_context_manager_delegates(self, clock):
        inner = MagicMock()
        inner.__aenter__ = AsyncMock(return_value=inner)
        inner.__aexit__ = AsyncMock(return_value=None)
        client = RateLimitedNetworkClient(inner, make_limiter(clock))
        async with client as c:
            assert c is client
        inner.__aenter__.assert_awaited_once()
        inner.__aexit__.assert_awaited_once()

    async def test_entered_object_is_kept_and_delegated_to(self, clock):
        entered = MagicMock()
        entered.get_rest_data = AsyncMock(return_value="from-entered")
        entered.marker = "entered-attr"
        inner = MagicMock()
        inner.__aenter__ = AsyncMock(return_value=entered)
        inner.__aexit__ = AsyncMock(return_value=None)
        inner.get_rest_data = AsyncMock(return_value="from-inner")
        client = RateLimitedNetworkClient(inner, make_limiter(clock))

        async with client as c:
            assert c is client
            assert await c.get_rest_data(url="http://x") == "from-entered"
            assert c.marker == "entered-attr"

        inner.get_rest_data.assert_not_awaited()
        inner.__aexit__.assert_awaited_once()


class TestSyncOnlyAdapterIsLimited:
    async def test_sync_adapter_fetch_acquires_limiter(self, clock):
        from candles_feed.adapters.adapter_mixins import SyncOnlyAdapter

        class FakeSync(SyncOnlyAdapter):
            REST_RATE_LIMIT = RestRateLimit(1, 3.0)

            def fetch_rest_candles_synchronous(
                self, trading_pair, interval, start_time=None, limit=500
            ):
                return []

        get_rate_limiter(
            pool_key_for(FakeSync), FakeSync.REST_RATE_LIMIT, clock=clock, sleep=clock.sleep
        )
        adapter = FakeSync()
        await adapter.fetch_rest_candles("BTC-USDT", "1m")
        await adapter.fetch_rest_candles("BTC-USDT", "1m")
        assert clock.sleeps == [pytest.approx(3.0)]


class CountingLimiter:
    """Minimal RestRateLimiterProtocol implementation that counts acquisitions."""

    def __init__(self) -> None:
        self.acquisitions = 0

    async def acquire(self) -> None:
        self.acquisitions += 1


class TestInjectedLimiter:
    @staticmethod
    def _make_feed(adapter, inner_client, limiter=None) -> CandlesFeed:
        with (
            patch(
                "candles_feed.hb_compat.hummingbot_network_client_adapter."
                "NetworkClientFactory.create_client",
                return_value=inner_client,
            ),
            patch.object(ExchangeRegistry, "get_adapter_instance", return_value=adapter),
        ):
            return CandlesFeed(
                exchange="binance_spot",
                trading_pair="BTC-USDT",
                interval="1m",
                rate_limiter=limiter,
            )

    def test_counting_limiter_satisfies_protocol(self):
        from candles_feed.core.protocols import RestRateLimiterProtocol

        assert isinstance(CountingLimiter(), RestRateLimiterProtocol)
        assert isinstance(make_limiter(FakeClock()), RestRateLimiterProtocol)

    async def test_async_path_uses_injected_limiter_not_registry(self):
        from candles_feed.core import rate_limiter as module

        inner = MagicMock()
        inner.get_rest_data = AsyncMock(return_value=[])
        limiter = CountingLimiter()
        feed = self._make_feed(BinanceSpotAdapter(), inner, limiter)

        await feed._adapter.fetch_rest_candles(
            "BTCUSDT", "1m", limit=10, network_client=feed._network_client
        )

        assert limiter.acquisitions == 1  # exactly one acquisition per request
        assert inner.get_rest_data.await_count == 1
        assert module._LIMITERS == {}

    async def test_sync_adapter_path_uses_the_same_injected_limiter(self):
        from candles_feed.adapters.adapter_mixins import SyncOnlyAdapter
        from candles_feed.core import rate_limiter as module

        class FakeSync(SyncOnlyAdapter):
            def get_trading_pair_format(self, trading_pair):
                return trading_pair

            def fetch_rest_candles_synchronous(
                self, trading_pair, interval, start_time=None, limit=500
            ):
                return []

        limiter = CountingLimiter()
        feed = self._make_feed(FakeSync(), MagicMock(), limiter)

        await feed._adapter.fetch_rest_candles("BTC-USDT", "1m")

        assert limiter.acquisitions == 1
        assert module._LIMITERS == {}

    async def test_injection_is_per_feed(self, clock, monkeypatch):
        monkeypatch.setattr(BinanceSpotAdapter, "REST_RATE_LIMIT", RestRateLimit(5, 1.0))
        inner = MagicMock()
        inner.get_rest_data = AsyncMock(return_value=[])
        injected = CountingLimiter()
        shared = get_rate_limiter(
            pool_key_for(BinanceSpotAdapter), RestRateLimit(5, 1.0), clock=clock, sleep=clock.sleep
        )
        feed_injected = self._make_feed(BinanceSpotAdapter(), inner, injected)
        feed_default = self._make_feed(BinanceSpotAdapter(), inner)

        await feed_default._network_client.get_rest_data(url="http://x")

        assert injected.acquisitions == 0
        assert len(shared._timestamps) == 1
        await feed_injected._network_client.get_rest_data(url="http://x")
        assert injected.acquisitions == 1
        assert len(shared._timestamps) == 1

    def test_resolve_without_injection_returns_shared_pool(self):
        from candles_feed.core.rate_limiter import (
            get_adapter_rate_limiter,
            resolve_adapter_rate_limiter,
            set_adapter_rate_limiter,
        )

        adapter = BinanceSpotAdapter()
        assert resolve_adapter_rate_limiter(adapter) is get_adapter_rate_limiter(adapter)
        limiter = CountingLimiter()
        set_adapter_rate_limiter(adapter, limiter)
        assert resolve_adapter_rate_limiter(adapter) is limiter
        assert resolve_adapter_rate_limiter(BinanceSpotAdapter) is get_adapter_rate_limiter(adapter)
        set_adapter_rate_limiter(adapter, None)
        assert resolve_adapter_rate_limiter(adapter) is get_adapter_rate_limiter(adapter)


class TestAdapterRestFetchIsLimited:
    @staticmethod
    def _make_feed(inner_client) -> CandlesFeed:
        with (
            patch(
                "candles_feed.hb_compat.hummingbot_network_client_adapter."
                "NetworkClientFactory.create_client",
                return_value=inner_client,
            ),
            patch.object(
                ExchangeRegistry, "get_adapter_instance", return_value=BinanceSpotAdapter()
            ),
        ):
            return CandlesFeed(exchange="binance_spot", trading_pair="BTC-USDT", interval="1m")

    async def test_rest_fetch_goes_through_limiter(self, clock, monkeypatch):
        monkeypatch.setattr(BinanceSpotAdapter, "REST_RATE_LIMIT", RestRateLimit(1, 5.0))
        inner = MagicMock()
        inner.get_rest_data = AsyncMock(return_value=[])
        get_rate_limiter(
            pool_key_for(BinanceSpotAdapter), RestRateLimit(1, 5.0), clock=clock, sleep=clock.sleep
        )
        feed = self._make_feed(inner)

        await feed._adapter.fetch_rest_candles(
            "BTCUSDT", "1m", limit=10, network_client=feed._network_client
        )
        await feed._adapter.fetch_rest_candles(
            "BTCUSDT", "1m", limit=10, network_client=feed._network_client
        )

        assert inner.get_rest_data.await_count == 2
        assert clock.sleeps == [pytest.approx(5.0)]

    async def test_two_feeds_for_same_exchange_share_limiter(self, clock, monkeypatch):
        monkeypatch.setattr(BinanceSpotAdapter, "REST_RATE_LIMIT", RestRateLimit(1, 5.0))
        inner = MagicMock()
        inner.get_rest_data = AsyncMock(return_value=[])
        get_rate_limiter(
            pool_key_for(BinanceSpotAdapter), RestRateLimit(1, 5.0), clock=clock, sleep=clock.sleep
        )
        feed1 = self._make_feed(inner)
        feed2 = self._make_feed(inner)

        await feed1._network_client.get_rest_data(url="http://x")
        await feed2._network_client.get_rest_data(url="http://x")

        assert clock.sleeps == [pytest.approx(5.0)]
