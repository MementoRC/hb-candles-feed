"""
REST rate limiting for the Candle Feed framework.

Every REST call an adapter makes is paced by a sliding-window limiter. Limiters
are shared process-wide per *pool*: by default one pool per adapter class, or an
explicit ``REST_RATE_LIMIT_POOL`` string when several adapters (e.g. spot and
perpetual of one exchange) draw from the same exchange-side budget.

Per-exchange declared limits and their sources are tabulated in docs/adapters/rest_rate_limits.md.

Request weights are not modelled yet (every call costs 1); that is a follow-up.

Known limitations: limiters assume a single asyncio thread, so concurrent use from
other threads or event loops may exceed the budget. ``SyncOnlyAdapter`` acquires the
permit before handing work to the executor, so calls queued behind busy executor
workers can start close together.
"""

import asyncio
import math
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RestRateLimit:
    """Allow at most ``max_requests`` REST calls per ``period_seconds``."""

    max_requests: int
    period_seconds: float

    def __post_init__(self) -> None:
        if self.max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if not math.isfinite(self.period_seconds) or self.period_seconds <= 0:
            raise ValueError("period_seconds must be a finite number > 0")


# Used when an adapter does not declare REST_RATE_LIMIT.
DEFAULT_REST_RATE_LIMIT = RestRateLimit(max_requests=5, period_seconds=1.0)


class AsyncRateLimiter:
    """Sliding-window limiter with injectable clock and sleep (for tests)."""

    def __init__(
        self,
        limit: RestRateLimit,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.limit = limit
        self._clock = clock
        self._sleep = sleep
        self._timestamps: deque[float] = deque()
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None

    def _get_lock(self) -> asyncio.Lock:
        """Return a lock bound to the running loop.

        Limiters are process-wide but an asyncio.Lock binds to the first loop that
        contends on it, so the lock is recreated per loop. The timestamps stay shared.
        """
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock

    async def acquire(self) -> None:
        """Wait until a request may be sent, then record it."""
        async with self._get_lock():
            now = self._clock()
            self._evict(now)
            if len(self._timestamps) >= self.limit.max_requests:
                wait = self._timestamps[0] + self.limit.period_seconds - now
                if wait > 0:
                    await self._sleep(wait)
                now = self._clock()
                self._evict(now)
            self._timestamps.append(now)

    def _evict(self, now: float) -> None:
        cutoff = now - self.limit.period_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()


_LIMITERS: dict[str, AsyncRateLimiter] = {}


def pool_key_for(adapter: Any) -> str:
    """Return the rate-limit pool key for an adapter class or instance."""
    cls = adapter if isinstance(adapter, type) else type(adapter)
    pool = getattr(cls, "REST_RATE_LIMIT_POOL", None)
    if isinstance(pool, str) and pool:
        return pool
    return f"{cls.__module__}.{cls.__qualname__}"


def rest_limit_for(adapter: Any) -> RestRateLimit:
    """Return the adapter's declared limit, or the conservative default."""
    limit = getattr(adapter, "REST_RATE_LIMIT", None)
    return limit if isinstance(limit, RestRateLimit) else DEFAULT_REST_RATE_LIMIT


def get_rate_limiter(
    pool_key: str,
    limit: RestRateLimit,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> AsyncRateLimiter:
    """Return the process-wide limiter for a pool, creating it on first use.

    The first caller's limit, clock and sleep win; later callers get the same instance.
    """
    limiter = _LIMITERS.get(pool_key)
    if limiter is None:
        limiter = _LIMITERS[pool_key] = AsyncRateLimiter(limit, clock=clock, sleep=sleep)
    return limiter


def get_adapter_rate_limiter(adapter: Any) -> AsyncRateLimiter:
    """Return the shared limiter for an adapter class or instance."""
    return get_rate_limiter(pool_key_for(adapter), rest_limit_for(adapter))


def reset_rate_limiters() -> None:
    """Drop all registered limiters (test isolation)."""
    _LIMITERS.clear()


class RateLimitedNetworkClient:
    """Network client proxy that paces ``get_rest_data`` through a limiter.

    Everything else (websockets, session lifecycle, ...) is delegated untouched.
    """

    def __init__(self, client: Any, limiter: AsyncRateLimiter) -> None:
        self._client = client
        self._target = client  # object entered via __aenter__, if it differs from the client
        self._limiter = limiter

    async def get_rest_data(self, *args: Any, **kwargs: Any) -> Any:
        """Wait for the rate limiter, then perform the REST request."""
        await self._limiter.acquire()
        return await self._target.get_rest_data(*args, **kwargs)

    async def __aenter__(self) -> Any:
        entered = await self._client.__aenter__()
        if entered is not None and entered is not self._client:
            self._target = entered
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        return await self._client.__aexit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)
