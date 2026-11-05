"""Runs hb-rate-limit's conformance suites against the candles-feed rate limiter."""

from collections.abc import Callable, Iterator

import pytest
from rate_limit import BackoffPolicy, RateLimit, RateLimiter
from rate_limit.testing import (
    assert_conforms_bound_retry_after_cap,
    assert_conforms_bound_unpausable,
    assert_conforms_pausable,
)
from rate_limit.types import Clock, Sleep

from candles_feed.core.rate_limiter import (
    AsyncRateLimiter,
    RestRateLimit,
    reset_rate_limiters,
)


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    reset_rate_limiters()
    yield
    reset_rate_limiters()


def test_async_rate_limiter_conforms_pausable() -> None:
    def make(clock: Clock, sleep: Sleep) -> AsyncRateLimiter:
        return AsyncRateLimiter(RestRateLimit(10, 1.0), clock, sleep)

    tier = assert_conforms_pausable(make, require_pool_pause=True)

    assert tier == "pool_pause"


def test_async_rate_limiter_conforms_bound_unpausable() -> None:
    """candles-feed never unpauses today; this guards the contract in case it starts to."""

    def make(rate_limit: RateLimit, clock: Clock, sleep: Sleep) -> AsyncRateLimiter:
        limiter = RateLimiter([rate_limit], clock=clock, sleep=sleep)
        return AsyncRateLimiter(
            RestRateLimit(rate_limit.limit, rate_limit.time_interval),
            name=rate_limit.limit_id,
            limiter=limiter,
        )

    assert_conforms_bound_unpausable(make)


def test_async_rate_limiter_conforms_bound_retry_after_cap() -> None:
    """candles-feed sets no Retry-After cap today; this guards the contract in case it does."""

    def make(
        cap: float, clock: Clock, backoff_factory: Callable[[], BackoffPolicy]
    ) -> AsyncRateLimiter:
        limiter = RateLimiter(
            [RateLimit("candles-feed:rest", 10, 1.0)],
            clock=clock,
            backoff_factory=backoff_factory,
            max_retry_after_seconds=cap,
        )
        return AsyncRateLimiter(RestRateLimit(10, 1.0), limiter=limiter)

    assert_conforms_bound_retry_after_cap(make)
