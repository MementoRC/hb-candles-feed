"""Tests for ConnectorThrottlerBridge: sharing a host connector's rate-limit budget (#89)."""

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import ClassVar

import pytest
from rate_limit.testing import assert_conforms_pausable
from rate_limit.types import Clock, Sleep

from candles_feed.hb_compat._web_stack import import_web_stack  # noqa: E402

try:  # hummingbot, or the standalone hb-web-assistant (the `test-hb` pixi env)
    AsyncThrottler = import_web_stack("throttler", "async_throttler").AsyncThrottler
    RateLimit = import_web_stack("throttler", "data_types").RateLimit
except ImportError:
    pytest.skip("neither hummingbot nor hb-web-assistant is installed", allow_module_level=True)

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter  # noqa: E402
from candles_feed.core.protocols import RestRateLimiterProtocol  # noqa: E402
from candles_feed.core.rate_limiter import (  # noqa: E402
    RateLimitPoolConflictError,
    RestRateLimit,
    pool_key_for,
    reset_rate_limiters,
    resolve_adapter_rate_limiter,
)
from candles_feed.hb_compat.data_types import CandlesConfig  # noqa: E402
from candles_feed.hb_compat.factory import CandlesFactory  # noqa: E402
from candles_feed.hb_compat.throttler_bridge import ConnectorThrottlerBridge  # noqa: E402

HOST_ID = "REQUEST_WEIGHT"


class HostedAdapter:
    REST_RATE_LIMIT = RestRateLimit(10, 1.0)
    REST_RATE_LIMIT_POOL: ClassVar[str] = "unit-pool"
    REST_HOST_RATE_LIMIT_ID: ClassVar[str | None] = HOST_ID
    REST_HOST_RATE_LIMIT_WEIGHT: ClassVar[int] = 2


class UnhostedAdapter(HostedAdapter):
    REST_HOST_RATE_LIMIT_ID: ClassVar[str | None] = None


class TightAdapter(HostedAdapter):
    """A pool budget of two requests a minute, so a third must wait on it."""

    REST_RATE_LIMIT = RestRateLimit(2, 60.0)
    REST_RATE_LIMIT_POOL: ClassVar[str] = "tight-pool"


def make_throttler(*, with_host: bool = True) -> AsyncThrottler:
    limits = [RateLimit(HOST_ID, limit=1200, time_interval=60)] if with_host else []
    limits.append(RateLimit("unrelated", limit=5, time_interval=1))
    return AsyncThrottler(limits)


def record_execute_task(monkeypatch: pytest.MonkeyPatch, throttler: AsyncThrottler) -> list[str]:
    """Record the limit ids ``throttler`` is asked to gate, through its public ``execute_task``."""
    calls: list[str] = []
    original = type(throttler).execute_task

    def execute_task(self, limit_id, *args, **kwargs):
        if self is throttler:
            calls.append(limit_id)
        return original(self, limit_id, *args, **kwargs)

    monkeypatch.setattr(type(throttler), "execute_task", execute_task)
    return calls


async def assert_waits(acquire) -> None:
    """``acquire()`` is held back: the budget it draws on is spent."""
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(acquire(), timeout=0.3)


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_rate_limiters()
    yield
    reset_rate_limiters()


def test_satisfies_rest_rate_limiter_protocol():
    bridge = ConnectorThrottlerBridge(make_throttler(), HostedAdapter())
    assert isinstance(bridge, RestRateLimiterProtocol)


def test_bridge_conforms_pausable():
    def make(clock: Clock, sleep: Sleep) -> ConnectorThrottlerBridge:
        # A fresh throttler per limiter: the pause is shared per (throttler, limit id).
        return ConnectorThrottlerBridge(make_throttler(), HostedAdapter(), clock=clock, sleep=sleep)

    tier = assert_conforms_pausable(make, require_pool_pause=True)

    assert tier == "pool_pause"


def test_registers_candles_feed_limit_for_pool():
    throttler = make_throttler()
    bridge = ConnectorThrottlerBridge(throttler, HostedAdapter())

    assert bridge.limit_id == f"candles-feed:unit-pool:{HOST_ID}"
    limit = throttler.get_related_limits(bridge.limit_id)[0]
    assert limit.limit == 10
    assert limit.time_interval == 1.0


def test_links_to_host_pool_with_weight():
    throttler = make_throttler()
    ConnectorThrottlerBridge(throttler, HostedAdapter())

    linked = throttler.get_related_limits(f"candles-feed:unit-pool:{HOST_ID}")[0].linked_limits
    assert [(pair.limit_id, pair.weight) for pair in linked] == [(HOST_ID, 2)]


async def test_request_consumes_weight_from_host_pool(monkeypatch):
    # A host pool of 4 a minute at weight 2: two requests fit, the third waits on the host.
    throttler = AsyncThrottler([RateLimit(HOST_ID, limit=4, time_interval=60)])
    bridge = ConnectorThrottlerBridge(throttler, HostedAdapter())
    calls = record_execute_task(monkeypatch, throttler)

    await bridge.acquire()
    await bridge.acquire()

    assert calls == [bridge.limit_id, bridge.limit_id]
    await assert_waits(bridge.acquire)


def test_unlinked_when_host_pool_missing(caplog):
    throttler = make_throttler(with_host=False)
    with caplog.at_level("INFO", logger="candles_feed.hb_compat.throttler_bridge"):
        ConnectorThrottlerBridge(throttler, HostedAdapter())

    assert throttler.get_related_limits("candles-feed:unit-pool")[0].linked_limits == []
    assert any(HOST_ID in record.getMessage() for record in caplog.records)


async def test_unlinked_bridge_still_paces_and_logs_only_own_limit(monkeypatch):
    throttler = make_throttler(with_host=False)
    bridge = ConnectorThrottlerBridge(throttler, TightAdapter())
    calls = record_execute_task(monkeypatch, throttler)

    await bridge.acquire()
    await bridge.acquire()

    assert calls == [bridge.limit_id, bridge.limit_id]
    await assert_waits(bridge.acquire)


def test_unlinked_when_adapter_declares_no_host_pool():
    throttler = make_throttler()
    ConnectorThrottlerBridge(throttler, UnhostedAdapter())
    assert throttler.get_related_limits("candles-feed:unit-pool")[0].linked_limits == []


def test_two_bridges_same_pool_share_one_limit():
    throttler = make_throttler()
    ConnectorThrottlerBridge(throttler, HostedAdapter())
    before = len(throttler._rate_limits)
    ConnectorThrottlerBridge(throttler, HostedAdapter())

    assert len(throttler._rate_limits) == before
    assert [rl.limit_id for rl in throttler._rate_limits].count(
        f"candles-feed:unit-pool:{HOST_ID}"
    ) == 1


class TestPoolConflicts:
    def test_different_limit_raises(self):
        throttler = make_throttler()
        ConnectorThrottlerBridge(throttler, HostedAdapter())

        class Bigger(HostedAdapter):
            REST_RATE_LIMIT = RestRateLimit(11, 1.0)

        with pytest.raises(RateLimitPoolConflictError, match="unit-pool"):
            ConnectorThrottlerBridge(throttler, Bigger())

    def test_different_period_raises(self):
        throttler = make_throttler()
        ConnectorThrottlerBridge(throttler, HostedAdapter())

        class Slower(HostedAdapter):
            REST_RATE_LIMIT = RestRateLimit(10, 2.0)

        with pytest.raises(RateLimitPoolConflictError):
            ConnectorThrottlerBridge(throttler, Slower())

    def test_different_host_weight_raises(self):
        throttler = make_throttler()
        ConnectorThrottlerBridge(throttler, HostedAdapter())

        class Heavier(HostedAdapter):
            REST_HOST_RATE_LIMIT_WEIGHT: ClassVar[int] = 3

        with pytest.raises(RateLimitPoolConflictError):
            ConnectorThrottlerBridge(throttler, Heavier())

    def test_different_host_ids_get_separate_limits_and_share_a_pause(self):
        throttler = AsyncThrottler(
            [
                RateLimit(HOST_ID, limit=1200, time_interval=60),
                RateLimit("OTHER_HOST", limit=600, time_interval=60),
            ]
        )

        class OtherHost(HostedAdapter):
            REST_HOST_RATE_LIMIT_ID: ClassVar[str | None] = "OTHER_HOST"

        first = ConnectorThrottlerBridge(throttler, HostedAdapter())
        second = ConnectorThrottlerBridge(throttler, OtherHost())

        assert first.limit_id == f"candles-feed:unit-pool:{HOST_ID}"
        assert second.limit_id == "candles-feed:unit-pool:OTHER_HOST"
        assert first.backoff is second.backoff
        assert not second.is_paused()
        first.pause(30)
        assert second.is_paused()

    def test_unlinked_and_linked_variants_do_not_conflict(self):
        throttler = make_throttler()
        linked = ConnectorThrottlerBridge(throttler, HostedAdapter())
        unlinked = ConnectorThrottlerBridge(throttler, UnhostedAdapter())
        assert linked.limit_id != unlinked.limit_id
        assert unlinked.limit_id == "candles-feed:unit-pool"

    def test_identical_limit_on_scaled_throttler_is_shared(self):
        throttler = AsyncThrottler(
            [RateLimit(HOST_ID, limit=1200, time_interval=60)],
            limits_share_percentage=Decimal("55"),
        )
        ConnectorThrottlerBridge(throttler, HostedAdapter())
        assert throttler.get_related_limits(f"candles-feed:unit-pool:{HOST_ID}")[0].limit == 5
        ConnectorThrottlerBridge(throttler, HostedAdapter())

    def test_throttler_without_get_related_limits_keeps_current_behaviour(self):
        class Bare:
            def __init__(self) -> None:
                self.added: list[RateLimit] = []

            def add_rate_limits(self, rate_limits: list[RateLimit]) -> None:
                self.added.extend(rate_limits)

        throttler = Bare()
        ConnectorThrottlerBridge(throttler, HostedAdapter())  # type: ignore[arg-type]
        ConnectorThrottlerBridge(throttler, HostedAdapter())  # type: ignore[arg-type]
        assert len(throttler.added) == 2


async def test_two_bridges_same_pool_draw_from_the_same_budget(monkeypatch):
    throttler = make_throttler()
    first = ConnectorThrottlerBridge(throttler, TightAdapter())
    second = ConnectorThrottlerBridge(throttler, TightAdapter())
    calls = record_execute_task(monkeypatch, throttler)

    await first.acquire()
    await second.acquire()

    assert first.limit_id == second.limit_id
    assert calls == [first.limit_id, first.limit_id]
    # The pool's two-a-minute budget is spent across both bridges.
    await assert_waits(first.acquire)


def test_default_pool_key_is_used_without_explicit_pool():
    class Plain:
        REST_RATE_LIMIT = RestRateLimit(3, 2.0)

    bridge = ConnectorThrottlerBridge(make_throttler(), Plain())
    assert bridge.limit_id == f"candles-feed:{pool_key_for(Plain)}"


class TestFromConnector:
    def test_returns_none_without_throttler(self):
        assert ConnectorThrottlerBridge.from_connector(SimpleNamespace(), HostedAdapter()) is None
        assert (
            ConnectorThrottlerBridge.from_connector(
                SimpleNamespace(throttler=None), HostedAdapter()
            )
            is None
        )
        assert ConnectorThrottlerBridge.from_connector(object(), HostedAdapter()) is None

    def test_builds_bridge_from_connector_throttler(self):
        throttler = make_throttler()
        bridge = ConnectorThrottlerBridge.from_connector(
            SimpleNamespace(throttler=throttler), HostedAdapter()
        )

        assert isinstance(bridge, ConnectorThrottlerBridge)
        assert throttler.get_related_limits(f"candles-feed:unit-pool:{HOST_ID}")[0] is not None


class TestFactoryWiring:
    def test_connector_with_throttler_wires_bridge_into_feed(self):
        throttler = make_throttler()
        connector = SimpleNamespace(throttler=throttler)

        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="binance", trading_pair="BTC-USDT"), connector=connector
        )

        limiter = resolve_adapter_rate_limiter(candle._feed._adapter)
        assert isinstance(limiter, ConnectorThrottlerBridge)
        assert limiter.limit_id == f"candles-feed:{pool_key_for(BinanceSpotAdapter)}:REQUEST_WEIGHT"
        assert throttler.get_related_limits(limiter.limit_id)[0] is not None

    async def test_feed_request_goes_through_bridge_once(self, monkeypatch):
        throttler = make_throttler()
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="binance", trading_pair="BTC-USDT"),
            connector=SimpleNamespace(throttler=throttler),
        )
        limiter = resolve_adapter_rate_limiter(candle._feed._adapter)
        calls = record_execute_task(monkeypatch, throttler)

        class Inner:
            async def get_rest_data(self, *args, **kwargs):
                return []

        candle._feed._network_client._target = Inner()
        await candle._feed._network_client.get_rest_data(url="http://x")

        assert calls == [limiter.limit_id]

    def test_connector_without_throttler_uses_shared_pool(self):
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="binance", trading_pair="BTC-USDT"),
            connector=SimpleNamespace(),
        )
        assert not isinstance(
            resolve_adapter_rate_limiter(candle._feed._adapter), ConnectorThrottlerBridge
        )
