"""Runs hb-rate-limit's conformance suites against the candles-feed rate limiter."""

from collections.abc import Iterator

import pytest
from rate_limit.testing import assert_conforms_pausable
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
