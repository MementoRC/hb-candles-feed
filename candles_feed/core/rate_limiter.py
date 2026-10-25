"""
REST rate limiting for the Candle Feed framework.

Every REST call an adapter makes is paced by a sliding-window limiter. Limiters
are shared process-wide per *pool*: by default one pool per adapter class, or an
explicit ``REST_RATE_LIMIT_POOL`` string when several adapters (e.g. spot and
perpetual of one exchange) draw from the same exchange-side budget.

The limiter machinery (window, pause, backoff, error type, helpers) lives in the
``hb-rate-limit`` package (import name ``rate_limit``); this module re-exports it under
the historical names and keeps the candles-feed specific declarations
(``RestRateLimit``, adapter pool keys, adapter injection, the network client proxy).

Per-exchange declared limits and their sources are tabulated in docs/adapters/rest_rate_limits.md.

Request weights are not modelled yet (every call costs 1); that is a follow-up.

``SyncOnlyAdapter`` acquires the permit before handing work to the executor, so calls
queued behind busy executor workers can start close together.
"""

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

from rate_limit import (
    DEFAULT_418_BAN_SECONDS,
    DEFAULT_429_BACKOFF_BASE_SECONDS,
    DEFAULT_429_BACKOFF_CAP_SECONDS,
    LONG_RETRY_AFTER_WARN_SECONDS,
    RATE_LIMIT_STATUSES,
    BackoffPolicy,
    BoundLimiter,
    PauseState,
    RateLimit,
    RateLimiter,
    RateLimitExceededError,
    RateLimitPoolConflictError,
    get_pool_limiter,
    note_rate_limited,
    note_request_succeeded,
    parse_retry_after,
    reset_pool_limiters,
    run_paced,
    wait_out_deadline,
)

from candles_feed.core.protocols import RestRateLimiterProtocol

__all__ = [
    "DEFAULT_418_BAN_SECONDS",
    "DEFAULT_429_BACKOFF_BASE_SECONDS",
    "DEFAULT_429_BACKOFF_CAP_SECONDS",
    "DEFAULT_REST_RATE_LIMIT",
    "LONG_RETRY_AFTER_WARN_SECONDS",
    "RATE_LIMIT_STATUSES",
    "AsyncRateLimiter",
    "BackoffPolicy",
    "PauseState",
    "RateLimitExceededError",
    "RateLimitPoolConflictError",
    "RateLimitedNetworkClient",
    "RestRateLimit",
    "get_adapter_rate_limiter",
    "get_rate_limiter",
    "note_rate_limited",
    "note_request_succeeded",
    "parse_retry_after",
    "pool_key_for",
    "reset_rate_limiters",
    "resolve_adapter_rate_limiter",
    "rest_limit_for",
    "run_paced",
    "set_adapter_rate_limiter",
    "wait_out_deadline",
]


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

    def to_rate_limit(self, limit_id: str) -> RateLimit:
        """Return this declaration as an ``hb-rate-limit`` ``RateLimit`` named ``limit_id``."""
        return RateLimit(limit_id, self.max_requests, self.period_seconds)


# Used when an adapter does not declare REST_RATE_LIMIT.
DEFAULT_REST_RATE_LIMIT = RestRateLimit(max_requests=5, period_seconds=1.0)


class AsyncRateLimiter(BoundLimiter):
    """Sliding-window limiter over ``hb-rate-limit`` with the historical constructor.

    Adds the candles-feed attributes ``limit`` (the ``RestRateLimit`` declaration),
    ``name`` (pool key) and ``owner`` (registering adapter) to ``BoundLimiter``.
    """

    def __init__(
        self,
        limit: RestRateLimit,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        *,
        name: str | None = None,
        owner: str | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        limit_id = name or "candles-feed:rest"
        if limiter is None:
            limiter = RateLimiter([limit.to_rate_limit(limit_id)], clock=clock, sleep=sleep)
        super().__init__(limiter, limit_id)
        self.limit = limit
        self.name = name  # pool key, for log messages
        self.owner = owner  # adapter that registered the pool, for error messages


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
    owner: str | None = None,
) -> AsyncRateLimiter:
    """Return the process-wide limiter for a pool, creating it on first use.

    The first caller's clock and sleep win; later callers get the same instance.

    :param owner: Name of the registering adapter, used in conflict messages
    :raises RateLimitPoolConflictError: the pool exists with a different ``limit``
    """
    bound = get_pool_limiter(
        pool_key, limit.to_rate_limit(pool_key), clock=clock, sleep=sleep, owner=owner
    )
    cached = _LIMITERS.get(pool_key)
    if cached is None or cached.limiter is not bound.limiter:
        cached = _LIMITERS[pool_key] = AsyncRateLimiter(
            limit, name=pool_key, owner=owner, limiter=bound.limiter
        )
    return cached


_INJECTED_ATTR = "_injected_rest_rate_limiter"


def set_adapter_rate_limiter(adapter: Any, limiter: RestRateLimiterProtocol | None) -> None:
    """Make an adapter *instance* use ``limiter`` instead of its process-wide pool.

    Pass ``None`` to go back to the shared registry. The override is per instance, so
    other feeds of the same exchange keep using the registry.
    """
    setattr(adapter, _INJECTED_ATTR, limiter)


def get_adapter_rate_limiter(adapter: Any) -> AsyncRateLimiter:
    """Return the shared process-wide limiter for an adapter class or instance."""
    cls = adapter if isinstance(adapter, type) else type(adapter)
    return get_rate_limiter(
        pool_key_for(adapter), rest_limit_for(adapter), owner=f"{cls.__module__}.{cls.__qualname__}"
    )


def resolve_adapter_rate_limiter(adapter: Any) -> RestRateLimiterProtocol:
    """Return the limiter an adapter must acquire from before each REST request.

    An injected limiter (see ``set_adapter_rate_limiter``) wins; otherwise the shared pool.
    """
    if not isinstance(adapter, type):
        injected = getattr(adapter, _INJECTED_ATTR, None)
        if injected is not None:
            return cast("RestRateLimiterProtocol", injected)
    return get_adapter_rate_limiter(adapter)


def reset_rate_limiters() -> None:
    """Drop all registered limiters (test isolation)."""
    _LIMITERS.clear()
    reset_pool_limiters()


class RateLimitedNetworkClient:
    """Network client proxy that paces ``get_rest_data`` through a limiter.

    Everything else (websockets, session lifecycle, ...) is delegated untouched.
    """

    def __init__(self, client: Any, limiter: RestRateLimiterProtocol) -> None:
        self._client = client
        self._target = client  # object entered via __aenter__, if it differs from the client
        self._limiter = limiter

    async def get_rest_data(self, *args: Any, **kwargs: Any) -> Any:
        """Wait for the rate limiter, then perform the REST request.

        A ``RateLimitExceededError`` pauses the limiter's pool before it propagates.
        """
        return await run_paced(self._limiter, lambda: self._target.get_rest_data(*args, **kwargs))

    async def __aenter__(self) -> Any:
        entered = await self._client.__aenter__()
        if entered is not None and entered is not self._client:
            self._target = entered
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any:
        return await self._client.__aexit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)
