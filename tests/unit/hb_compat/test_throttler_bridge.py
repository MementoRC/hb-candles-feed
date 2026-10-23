"""Tests for ConnectorThrottlerBridge: sharing a host connector's rate-limit budget (#89)."""

from types import SimpleNamespace
from typing import ClassVar

import pytest

pytest.importorskip("hummingbot.core.api_throttler.async_throttler")

from hummingbot.core.api_throttler.async_throttler import AsyncThrottler  # noqa: E402
from hummingbot.core.api_throttler.data_types import RateLimit  # noqa: E402

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter  # noqa: E402
from candles_feed.core.protocols import RestRateLimiterProtocol  # noqa: E402
from candles_feed.core.rate_limiter import (  # noqa: E402
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


def make_throttler(*, with_host: bool = True) -> AsyncThrottler:
    limits = [RateLimit(HOST_ID, limit=1200, time_interval=60)] if with_host else []
    limits.append(RateLimit("unrelated", limit=5, time_interval=1))
    return AsyncThrottler(limits)


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_rate_limiters()
    yield
    reset_rate_limiters()


def test_satisfies_rest_rate_limiter_protocol():
    bridge = ConnectorThrottlerBridge(make_throttler(), HostedAdapter())
    assert isinstance(bridge, RestRateLimiterProtocol)


def test_registers_candles_feed_limit_for_pool():
    throttler = make_throttler()
    bridge = ConnectorThrottlerBridge(throttler, HostedAdapter())

    assert bridge.limit_id == "candles-feed:unit-pool"
    limit = throttler._id_to_limit_map["candles-feed:unit-pool"]
    assert limit.limit == 10
    assert limit.time_interval == 1.0


def test_links_to_host_pool_with_weight():
    throttler = make_throttler()
    ConnectorThrottlerBridge(throttler, HostedAdapter())

    linked = throttler._id_to_limit_map["candles-feed:unit-pool"].linked_limits
    assert [(pair.limit_id, pair.weight) for pair in linked] == [(HOST_ID, 2)]


async def test_request_consumes_weight_from_host_pool():
    throttler = make_throttler()
    bridge = ConnectorThrottlerBridge(throttler, HostedAdapter())

    await bridge.acquire()
    await bridge.acquire()

    host_weight = sum(
        log.weight for log in throttler._task_logs if log.rate_limit.limit_id == HOST_ID
    )
    own_logs = [log for log in throttler._task_logs if log.rate_limit.limit_id == bridge.limit_id]
    assert host_weight == 4
    assert len(own_logs) == 2


def test_unlinked_when_host_pool_missing(caplog):
    throttler = make_throttler(with_host=False)
    with caplog.at_level("INFO", logger="candles_feed.hb_compat.throttler_bridge"):
        ConnectorThrottlerBridge(throttler, HostedAdapter())

    assert throttler._id_to_limit_map["candles-feed:unit-pool"].linked_limits == []
    assert any(HOST_ID in record.getMessage() for record in caplog.records)


async def test_unlinked_bridge_still_paces_and_logs_only_own_limit():
    throttler = make_throttler(with_host=False)
    bridge = ConnectorThrottlerBridge(throttler, HostedAdapter())

    await bridge.acquire()

    assert [log.rate_limit.limit_id for log in throttler._task_logs] == [bridge.limit_id]


def test_unlinked_when_adapter_declares_no_host_pool():
    throttler = make_throttler()
    ConnectorThrottlerBridge(throttler, UnhostedAdapter())
    assert throttler._id_to_limit_map["candles-feed:unit-pool"].linked_limits == []


def test_two_bridges_same_pool_share_one_limit():
    throttler = make_throttler()
    ConnectorThrottlerBridge(throttler, HostedAdapter())
    before = len(throttler._rate_limits)
    ConnectorThrottlerBridge(throttler, HostedAdapter())

    assert len(throttler._rate_limits) == before
    assert [rl.limit_id for rl in throttler._rate_limits].count("candles-feed:unit-pool") == 1


async def test_two_bridges_same_pool_draw_from_the_same_budget():
    throttler = make_throttler()
    first = ConnectorThrottlerBridge(throttler, HostedAdapter())
    second = ConnectorThrottlerBridge(throttler, HostedAdapter())

    await first.acquire()
    await second.acquire()

    own = [log for log in throttler._task_logs if log.rate_limit.limit_id == first.limit_id]
    assert len(own) == 2
    assert first.limit_id == second.limit_id


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
        assert "candles-feed:unit-pool" in throttler._id_to_limit_map


class TestFactoryWiring:
    def test_connector_with_throttler_wires_bridge_into_feed(self):
        throttler = make_throttler()
        connector = SimpleNamespace(throttler=throttler)

        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="binance", trading_pair="BTC-USDT"), connector=connector
        )

        limiter = resolve_adapter_rate_limiter(candle._feed._adapter)
        assert isinstance(limiter, ConnectorThrottlerBridge)
        assert limiter.limit_id == f"candles-feed:{pool_key_for(BinanceSpotAdapter)}"
        assert limiter.limit_id in throttler._id_to_limit_map

    async def test_feed_request_goes_through_bridge_once(self):
        throttler = make_throttler()
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="binance", trading_pair="BTC-USDT"),
            connector=SimpleNamespace(throttler=throttler),
        )
        limiter = resolve_adapter_rate_limiter(candle._feed._adapter)

        class Inner:
            async def get_rest_data(self, *args, **kwargs):
                return []

        candle._feed._network_client._target = Inner()
        await candle._feed._network_client.get_rest_data(url="http://x")

        own = [log for log in throttler._task_logs if log.rate_limit.limit_id == limiter.limit_id]
        assert len(own) == 1

    def test_connector_without_throttler_uses_shared_pool(self):
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="binance", trading_pair="BTC-USDT"),
            connector=SimpleNamespace(),
        )
        assert not isinstance(
            resolve_adapter_rate_limiter(candle._feed._adapter), ConnectorThrottlerBridge
        )
