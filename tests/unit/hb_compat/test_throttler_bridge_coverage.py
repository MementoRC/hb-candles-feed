"""Default-env tests for ConnectorThrottlerBridge.

The default environment has neither hummingbot nor hb-web-assistant, so the throttler stack
the bridge imports lazily is stood in for by ``rate_limit.hb_compat`` (the same legacy
``RateLimit`` / ``AsyncThrottler`` model), patched in through the bridge's
``import_web_stack`` hook. The fuller integration tests live in ``test_throttler_bridge.py``
and run in the ``test-hb`` environment.
"""

from decimal import Decimal
from types import SimpleNamespace
from typing import ClassVar

import pytest
from rate_limit.hb_compat import data_types
from rate_limit.hb_compat.async_throttler import AsyncThrottler

from candles_feed.core.rate_limiter import RateLimitPoolConflictError, RestRateLimit
from candles_feed.hb_compat import throttler_bridge
from candles_feed.hb_compat.throttler_bridge import (
    ConnectorThrottlerBridge,
    _check_same_limit,
    _owner_name,
    _registered_limit,
    _shared_state,
)

HOST_ID = "REQUEST_WEIGHT"


class PooledAdapter:
    REST_RATE_LIMIT = RestRateLimit(10, 1.0)
    REST_RATE_LIMIT_POOL: ClassVar[str] = "cov-pool"
    REST_HOST_RATE_LIMIT_ID: ClassVar[str | None] = HOST_ID
    REST_HOST_RATE_LIMIT_WEIGHT: ClassVar[int] = 3


class UnhostedAdapter(PooledAdapter):
    REST_HOST_RATE_LIMIT_ID: ClassVar[str | None] = None


class BiggerAdapter(PooledAdapter):
    REST_RATE_LIMIT = RestRateLimit(20, 1.0)


class FakeClock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class _Gate:
    def __init__(self, log: list[str], limit_id: str) -> None:
        self._log = log
        self._limit_id = limit_id

    async def __aenter__(self) -> None:
        self._log.append(f"enter:{self._limit_id}")

    async def __aexit__(self, *exc: object) -> None:
        self._log.append(f"exit:{self._limit_id}")


class MinimalThrottler:
    """A throttler exposing only what the bridge must have: no ``get_related_limits``."""

    def __init__(self) -> None:
        self.added: list = []
        self.log: list[str] = []

    def add_rate_limits(self, limits: list) -> None:
        self.added.extend(limits)

    def execute_task(self, limit_id: str) -> _Gate:
        return _Gate(self.log, limit_id)


@pytest.fixture(autouse=True)
def legacy_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_import(area: str, module: str):
        assert (area, module) == ("throttler", "data_types")
        return data_types

    monkeypatch.setattr(throttler_bridge, "import_web_stack", fake_import)


def host_throttler(**kwargs) -> AsyncThrottler:
    return AsyncThrottler([data_types.RateLimit(HOST_ID, limit=1200, time_interval=60)], **kwargs)


def make_bridge(throttler=None, adapter=PooledAdapter, clock=None):
    clock = clock or FakeClock()
    throttler = throttler if throttler is not None else host_throttler()
    return ConnectorThrottlerBridge(throttler, adapter, clock=clock, sleep=clock.sleep), throttler


# ---- module helpers ---------------------------------------------------------------------


def test_registered_limit_without_getter_is_none():
    assert _registered_limit(object(), "anything") is None


def test_registered_limit_reads_first_of_related_limits():
    throttler = host_throttler()
    assert _registered_limit(throttler, HOST_ID).limit == 1200
    assert _registered_limit(throttler, "missing") is None


def test_shared_state_is_per_throttler_and_limit_id():
    first, second = host_throttler(), host_throttler()
    assert _shared_state(first, "a") is _shared_state(first, "a")
    assert _shared_state(first, "a") is not _shared_state(first, "b")
    assert _shared_state(first, "a") is not _shared_state(second, "a")


def test_shared_state_for_unweakrefable_throttler_is_private():
    class Slotted:
        __slots__ = ()

    throttler = Slotted()
    assert _shared_state(throttler, "a") is not _shared_state(throttler, "a")


def test_owner_name_for_class_and_instance():
    expected = f"{PooledAdapter.__module__}.PooledAdapter"
    assert _owner_name(PooledAdapter) == expected
    assert _owner_name(PooledAdapter()) == expected


def _limit(limit: int, interval: float = 1.0, links: tuple = ()):
    pairs = [data_types.LinkedLimitWeightPair(name, weight) for name, weight in links]
    return data_types.RateLimit("id", limit, interval, linked_limits=pairs)


def test_check_same_limit_accepts_identical_definition():
    _check_same_limit(
        SimpleNamespace(),
        "pool",
        _limit(10, links=[("h", 2)]),
        _limit(10, links=[("h", 2)]),
        "owner",
    )


def test_check_same_limit_scales_request_by_throttler_pct():
    throttler = SimpleNamespace(limits_pct=Decimal("0.5"))
    _check_same_limit(throttler, "pool", _limit(5), _limit(10), "owner")
    # A request that scales to zero is floored at one.
    _check_same_limit(throttler, "pool", _limit(1), _limit(1), "owner")


@pytest.mark.parametrize(
    "requested",
    [_limit(11), _limit(10, interval=2.0), _limit(10, links=[("h", 1)])],
    ids=["limit", "interval", "links"],
)
def test_check_same_limit_rejects_any_difference(requested):
    with pytest.raises(RateLimitPoolConflictError) as excinfo:
        _check_same_limit(SimpleNamespace(), "pool", _limit(10), requested, "my.Owner")
    assert "pool" in str(excinfo.value)


# ---- construction -----------------------------------------------------------------------


def test_links_to_host_limit_when_throttler_defines_it():
    bridge, throttler = make_bridge()
    assert bridge.limit_id == f"candles-feed:cov-pool:{HOST_ID}"
    registered = throttler.get_limit(bridge.limit_id)
    assert (registered.limit, registered.time_interval) == (10, 1.0)
    assert [(p.limit_id, p.weight) for p in registered.linked_limits] == [(HOST_ID, 3)]


def test_unlinked_when_adapter_declares_no_host_pool():
    bridge, throttler = make_bridge(adapter=UnhostedAdapter)
    assert bridge.limit_id == "candles-feed:cov-pool"
    assert throttler.get_limit(bridge.limit_id).linked_limits == []


def test_unlinked_when_throttler_lacks_the_host_limit():
    bridge, throttler = make_bridge(throttler=AsyncThrottler([]))
    assert bridge.limit_id == "candles-feed:cov-pool"
    assert throttler.get_limit(bridge.limit_id).linked_limits == []


def test_default_limit_used_for_adapter_without_declared_limit():
    class Bare:
        pass

    bridge, throttler = make_bridge(adapter=Bare)
    assert bridge.limit_id.startswith("candles-feed:")
    assert Bare.__qualname__ in bridge.limit_id
    assert throttler.get_limit(bridge.limit_id) is not None


def test_same_definition_registers_once_and_conflicting_one_raises():
    throttler = host_throttler()
    first, _ = make_bridge(throttler)
    second, _ = make_bridge(throttler)
    assert first.limit_id == second.limit_id
    with pytest.raises(RateLimitPoolConflictError):
        make_bridge(throttler, adapter=BiggerAdapter)


def test_scaled_throttler_accepts_reregistration():
    throttler = host_throttler(limits_share_percentage=Decimal(50))
    first, _ = make_bridge(throttler)
    assert throttler.get_limit(first.limit_id).limit == 5
    make_bridge(throttler)


def test_throttler_without_get_related_limits_registers_unlinked():
    throttler = MinimalThrottler()
    bridge, _ = make_bridge(throttler)
    assert bridge.limit_id == "candles-feed:cov-pool"
    (registered,) = throttler.added
    assert registered.limit_id == bridge.limit_id
    assert registered.linked_limits == []


# ---- from_connector ---------------------------------------------------------------------


def test_from_connector_without_throttler_returns_none():
    assert ConnectorThrottlerBridge.from_connector(SimpleNamespace(), PooledAdapter) is None
    assert (
        ConnectorThrottlerBridge.from_connector(SimpleNamespace(throttler=None), PooledAdapter)
        is None
    )


def test_from_connector_builds_bridge_on_connector_throttler():
    throttler = host_throttler()
    bridge = ConnectorThrottlerBridge.from_connector(
        SimpleNamespace(throttler=throttler), PooledAdapter
    )
    assert isinstance(bridge, ConnectorThrottlerBridge)
    assert throttler.has_limit(bridge.limit_id)


def test_from_connector_returns_none_when_web_stack_missing(monkeypatch: pytest.MonkeyPatch):
    def missing(area: str, module: str):
        raise ImportError("no throttler stack")

    monkeypatch.setattr(throttler_bridge, "import_web_stack", missing)
    connector = SimpleNamespace(throttler=MinimalThrottler())
    assert ConnectorThrottlerBridge.from_connector(connector, PooledAdapter) is None
    assert connector.throttler.added == []


# ---- pause and acquire ------------------------------------------------------------------


def test_pause_blocks_until_deadline_and_never_shortens():
    clock = FakeClock(100.0)
    bridge, _ = make_bridge(clock=clock)
    assert not bridge.is_paused()
    assert bridge.blocked_for() == 0.0

    bridge.pause(5.0)
    assert bridge.is_paused()
    assert bridge.blocked_for() == pytest.approx(5.0)

    bridge.pause(1.0)  # shorter pause must not shorten the active one
    assert bridge.blocked_for() == pytest.approx(5.0)
    bridge.pause(-3.0)  # negative durations are clamped to zero
    assert bridge.blocked_for() == pytest.approx(5.0)

    clock.now += 5.0
    assert not bridge.is_paused()
    assert bridge.blocked_for() == 0.0


def test_pause_and_backoff_shared_between_bridges_on_same_throttler_and_pool():
    clock = FakeClock()
    throttler = host_throttler()
    first, _ = make_bridge(throttler, clock=clock)
    linked_twin, _ = make_bridge(throttler, clock=clock)
    other_throttler, _ = make_bridge(clock=clock)

    first.pause(7.0)
    assert linked_twin.is_paused()
    assert linked_twin.backoff is first.backoff
    assert not other_throttler.is_paused()
    assert other_throttler.backoff is not first.backoff


async def test_acquire_waits_out_pause_then_gates_on_limit():
    clock = FakeClock()
    throttler = MinimalThrottler()
    bridge, _ = make_bridge(throttler, clock=clock)
    bridge.pause(4.0)

    await bridge.acquire()

    assert sum(clock.sleeps) == pytest.approx(4.0)
    assert not bridge.is_paused()
    assert throttler.log == [f"enter:{bridge.limit_id}", f"exit:{bridge.limit_id}"]


async def test_acquire_without_pause_does_not_sleep():
    clock = FakeClock()
    throttler = MinimalThrottler()
    bridge, _ = make_bridge(throttler, clock=clock)

    await bridge.acquire()
    await bridge.acquire()

    assert clock.sleeps == []
    assert throttler.log.count(f"enter:{bridge.limit_id}") == 2


async def test_acquire_spends_from_real_throttler_budget():
    bridge, throttler = make_bridge()
    await bridge.acquire()
    assert throttler.has_limit(bridge.limit_id)
