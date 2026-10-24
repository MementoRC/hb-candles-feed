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
import logging
import math
import time
import weakref
from collections import deque
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Any, cast

from candles_feed.core.protocols import RestRateLimiterProtocol

logger = logging.getLogger(__name__)

# HTTP statuses meaning "stop sending": 429 rate limited, 418 IP banned (Binance).
RATE_LIMIT_STATUSES = frozenset({418, 429})

# Backoff defaults when the exchange sends no Retry-After.
DEFAULT_429_BACKOFF_BASE_SECONDS = 5.0  # first pause; doubles per consecutive 429
DEFAULT_429_BACKOFF_CAP_SECONDS = 300.0
DEFAULT_418_BAN_SECONDS = 120.0
LONG_RETRY_AFTER_WARN_SECONDS = 3600.0  # honoured anyway, but flagged in the log


def parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header (delta-seconds or HTTP-date) into seconds.

    :param value: Raw header value
    :return: Seconds to wait (negatives clamp to 0), or None when absent or unparseable
    """
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    try:
        seconds = float(text)
    except ValueError:
        try:
            moment = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        seconds = moment.timestamp() - time.time()
    if not math.isfinite(seconds):
        return None
    return max(0.0, seconds)


def _header(headers: Mapping[str, str] | None, name: str) -> str | None:
    """Case-insensitive header lookup that also works for plain dicts."""
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value
    return None


class RateLimitExceededError(Exception):
    """The exchange answered HTTP 429 (rate limited) or 418 (IP banned).

    :ivar status: The HTTP status (429 or 418; 429 for CCXT's rate-limit exceptions)
    :ivar retry_after: Seconds the exchange asked us to wait, or None if it did not say
    """

    def __init__(self, status: int, retry_after: float | None = None, message: str = "") -> None:
        super().__init__(message or f"HTTP {status}: rate limited (retry_after={retry_after})")
        self.status = status
        self.retry_after = retry_after

    @classmethod
    def from_response(
        cls, status: int, headers: Mapping[str, str] | None = None, message: str = ""
    ) -> "RateLimitExceededError":
        """Build the error from a response status and its headers."""
        return cls(status, parse_retry_after(_header(headers, "Retry-After")), message)


class BackoffPolicy:
    """Pause length for the next rate-limit response, tracked per limiter.

    ``Retry-After`` wins. Otherwise 418 pauses for ``ban_seconds`` and 429 backs off
    exponentially (``base``, ``2*base``, ... up to ``cap``) while 429s keep arriving; the
    streak resets on the next successful request.
    """

    def __init__(
        self,
        base_seconds: float = DEFAULT_429_BACKOFF_BASE_SECONDS,
        cap_seconds: float = DEFAULT_429_BACKOFF_CAP_SECONDS,
        ban_seconds: float = DEFAULT_418_BAN_SECONDS,
    ) -> None:
        self.base_seconds = base_seconds
        self.cap_seconds = cap_seconds
        self.ban_seconds = ban_seconds
        self.streak = 0

    def next_delay(self, status: int, retry_after: float | None, in_burst: bool = False) -> float:
        """Register one rate-limit response and return how long to pause.

        :param in_burst: The pool was already paused when this response arrived, i.e. it
            belongs to requests that were in flight when the pause began. A 429 without
            ``Retry-After`` then neither escalates the streak nor extends the pause (0).
        """
        if in_burst and status != 418 and retry_after is None:
            return 0.0
        self.streak += 1
        if retry_after is not None:
            return retry_after
        if status == 418:
            return self.ban_seconds
        return min(self.cap_seconds, self.base_seconds * 2 ** (self.streak - 1))

    def reset(self) -> None:
        """Forget the streak (a request succeeded)."""
        self.streak = 0


@dataclass
class PauseState:
    """Pause deadline plus backoff streak, shared by everything on one limit."""

    deadline: float = 0.0
    backoff: BackoffPolicy = field(default_factory=BackoffPolicy)


async def wait_out_deadline(
    get_deadline: Callable[[], float],
    clock: Callable[[], float],
    sleep: Callable[[float], Awaitable[None]],
) -> None:
    """Sleep until the (possibly extended meanwhile) deadline has passed."""
    while (remaining := get_deadline() - clock()) > 0:
        await sleep(remaining)


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


class RateLimitPoolConflictError(ValueError):
    """Two adapters sharing one rate-limit pool declare different limits."""

    def __init__(
        self,
        pool: str,
        existing: object,
        requested: object,
        existing_owner: str | None = None,
        requested_owner: str | None = None,
    ) -> None:
        by = f" (registered by {existing_owner})" if existing_owner else ""
        asker = f" by {requested_owner}" if requested_owner else ""
        super().__init__(
            f"Rate-limit pool {pool!r} already has limit {existing}{by}; "
            f"conflicting limit {requested} requested{asker}. "
            "Adapters sharing a REST_RATE_LIMIT_POOL must declare identical limits."
        )
        self.pool = pool


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
        self.name: str | None = None  # pool key, for log messages
        self.owner: str | None = None  # adapter that registered the pool, for error messages
        self._pause = PauseState()

    @property
    def backoff(self) -> BackoffPolicy:
        """Backoff policy (streak state) of this limiter."""
        return self._pause.backoff

    def pause(self, seconds: float) -> None:
        """Block every ``acquire`` for ``seconds`` (never shortens an existing pause).

        The deadline is a plain clock value, not tied to an event loop, so feeds on
        other loops sharing this limiter stop as well.
        """
        self._pause.deadline = max(self._pause.deadline, self._clock() + max(0.0, seconds))

    def is_paused(self) -> bool:
        """Whether a pause is currently active."""
        return self._pause.deadline > self._clock()

    async def _wait_out_pause(self) -> None:
        await wait_out_deadline(lambda: self._pause.deadline, self._clock, self._sleep)

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
        # Wait out a pause before queueing on the lock, so paused callers do not pile up
        # behind it; re-checked after the window sleep in case a pause arrived meanwhile.
        await self._wait_out_pause()
        async with self._get_lock():
            now = self._clock()
            self._evict(now)
            if len(self._timestamps) >= self.limit.max_requests:
                wait = self._timestamps[0] + self.limit.period_seconds - now
                if wait > 0:
                    await self._sleep(wait)
                await self._wait_out_pause()
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
    owner: str | None = None,
) -> AsyncRateLimiter:
    """Return the process-wide limiter for a pool, creating it on first use.

    The first caller's clock and sleep win; later callers get the same instance.

    :param owner: Name of the registering adapter, used in conflict messages
    :raises RateLimitPoolConflictError: the pool exists with a different ``limit``
    """
    limiter = _LIMITERS.get(pool_key)
    if limiter is None:
        limiter = _LIMITERS[pool_key] = AsyncRateLimiter(limit, clock=clock, sleep=sleep)
        limiter.name = pool_key
        limiter.owner = owner
    elif limiter.limit != limit:
        raise RateLimitPoolConflictError(pool_key, limiter.limit, limit, limiter.owner, owner)
    return limiter


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


_FALLBACK_POLICIES: "weakref.WeakKeyDictionary[Any, BackoffPolicy]" = weakref.WeakKeyDictionary()
_UNPAUSABLE_WARNED: "weakref.WeakSet[Any]" = weakref.WeakSet()


def _backoff_for(limiter: Any) -> BackoffPolicy:
    """Return the limiter's backoff policy, attaching a per-instance one if it has none."""
    policy = getattr(limiter, "backoff", None)
    if isinstance(policy, BackoffPolicy):
        return policy
    try:
        return _FALLBACK_POLICIES.setdefault(limiter, BackoffPolicy())
    except TypeError:  # not weak-referenceable: no streak memory
        return BackoffPolicy()


def _limiter_label(limiter: Any) -> str:
    return str(
        getattr(limiter, "name", None)
        or getattr(limiter, "limit_id", None)
        or type(limiter).__name__
    )


def note_rate_limited(limiter: RestRateLimiterProtocol, exc: RateLimitExceededError) -> None:
    """Pause ``limiter``'s whole pool after a 429/418 and log one warning for the event.

    Limiters without ``pause()`` cannot back off: that is logged once and nothing else
    happens (the caller re-raises the error).
    """
    pause = getattr(limiter, "pause", None)
    if not callable(pause):
        try:
            if limiter not in _UNPAUSABLE_WARNED:
                _UNPAUSABLE_WARNED.add(limiter)
                logger.warning(
                    "Rate limiter %s cannot pause; no backoff after HTTP %s",
                    _limiter_label(limiter),
                    exc.status,
                )
        except TypeError:
            pass
        return
    is_paused = getattr(limiter, "is_paused", None)
    in_burst = bool(is_paused()) if callable(is_paused) else False
    delay = _backoff_for(limiter).next_delay(exc.status, exc.retry_after, in_burst)
    if delay == 0.0 and in_burst:
        logger.debug("HTTP %s on %s joins the active pause", exc.status, _limiter_label(limiter))
        return
    pause(delay)
    note = (
        " (unusually long Retry-After, honoured)"
        if exc.retry_after is not None and exc.retry_after > LONG_RETRY_AFTER_WARN_SECONDS
        else ""
    )
    logger.warning(
        "Rate limited (HTTP %s) on %s; pausing all requests in the pool for %.1fs%s",
        exc.status,
        _limiter_label(limiter),
        delay,
        note,
    )


def note_request_succeeded(limiter: RestRateLimiterProtocol) -> None:
    """Reset the 429 streak of ``limiter`` after a successful request."""
    policy = getattr(limiter, "backoff", None)
    if not isinstance(policy, BackoffPolicy):
        try:
            policy = _FALLBACK_POLICIES.get(limiter)
        except TypeError:
            return
    if policy is not None:
        policy.reset()


async def run_paced[T](limiter: RestRateLimiterProtocol, call: Callable[[], Awaitable[T]]) -> T:
    """Acquire once, run ``call``, and apply rate-limit backoff bookkeeping.

    A ``RateLimitExceededError`` pauses the limiter's pool and propagates; success resets
    the backoff streak. Every REST path (async client, sync executor, thread fallback)
    goes through here so they all behave identically.
    """
    await limiter.acquire()
    try:
        result = await call()
    except RateLimitExceededError as exc:
        note_rate_limited(limiter, exc)
        raise
    note_request_succeeded(limiter)
    return result


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
