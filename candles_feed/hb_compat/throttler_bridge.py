"""Bridge from a hummingbot connector's throttler to the feed's REST rate limiter.

Lets a feed created next to a connector (``CandlesFactory.get_candle(config, connector)``)
spend from the connector's shared rate-limit budget, so the feed's klines requests and the
connector's own requests are paced together instead of racing for the exchange's limit.
"""

import asyncio
import logging
import math
import time
import weakref
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

from candles_feed.core.protocols import AsyncThrottlerProtocol
from candles_feed.core.rate_limiter import (
    BackoffPolicy,
    PauseState,
    RateLimitPoolConflictError,
    pool_key_for,
    rest_limit_for,
    wait_out_deadline,
)
from candles_feed.hb_compat._web_stack import import_web_stack

logger = logging.getLogger(__name__)

# Pause deadline + backoff streak per (throttler, limit id), so bridges that share a
# limit on the host throttler also share a pause.
_SHARED_STATES: "weakref.WeakKeyDictionary[Any, dict[str, PauseState]]" = (
    weakref.WeakKeyDictionary()
)


def _registered_limit(throttler: Any, limit_id: str) -> Any:
    """The throttler's registered ``RateLimit`` for ``limit_id``, or None if absent.

    Uses the public ``get_related_limits``; a throttler without it counts as having none.
    """
    getter = getattr(throttler, "get_related_limits", None)
    if getter is None:
        return None
    return getter(limit_id)[0]


def _shared_state(throttler: Any, limit_id: str) -> PauseState:
    try:
        return _SHARED_STATES.setdefault(throttler, {}).setdefault(limit_id, PauseState())
    except TypeError:  # throttler cannot be weak-referenced: pause is per bridge only
        return PauseState()


def _owner_name(adapter: Any) -> str:
    cls = adapter if isinstance(adapter, type) else type(adapter)
    return f"{cls.__module__}.{cls.__qualname__}"


def _describe(rate_limit: Any, limit: Any) -> str:
    links = [(pair.limit_id, pair.weight) for pair in rate_limit.linked_limits]
    return f"{limit} per {rate_limit.time_interval}s linked to {links}"


def _check_same_limit(throttler: Any, pool: str, existing: Any, requested: Any, owner: str) -> None:
    """Raise when a limit already on the throttler differs from the one being requested.

    The throttler skips duplicate ids silently and scales stored limits by ``limits_pct``,
    so the request is compared after the same scaling.
    """
    pct = Decimal(str(getattr(throttler, "limits_pct", 1)))
    scaled = max(Decimal(1), math.floor(Decimal(str(requested.limit)) * pct))
    same = (
        Decimal(str(existing.limit)) == scaled
        and existing.time_interval == requested.time_interval
        and [(p.limit_id, p.weight) for p in existing.linked_limits]
        == [(p.limit_id, p.weight) for p in requested.linked_limits]
    )
    if not same:
        raise RateLimitPoolConflictError(
            pool,
            _describe(existing, existing.limit),
            _describe(requested, scaled),
            requested_owner=owner,
        )


class ConnectorThrottlerBridge:
    """``RestRateLimiterProtocol`` implementation backed by a hummingbot throttler.

    Registers one rate limit sized from the adapter's ``REST_RATE_LIMIT``. When the adapter
    names a host pool (``REST_HOST_RATE_LIMIT_ID``) that the throttler already defines, the
    limit is ``candles-feed:<pool>:<host id>`` and is linked to it with
    ``REST_HOST_RATE_LIMIT_WEIGHT``, so each request also consumes the host budget.
    Otherwise it is ``candles-feed:<pool>``, unlinked, and only paces the feed itself.

    Bridges on the same throttler and limit id share one limit (registration is additive);
    a different definition under the same id raises ``RateLimitPoolConflictError``. The
    429/418 pause is shared per pool, across host links.
    """

    def __init__(
        self,
        throttler: AsyncThrottlerProtocol,
        adapter: Any,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        # Imported here so that importing this module never requires hummingbot
        # (or the standalone hb-web-assistant that stands in for it).
        data_types = import_web_stack("throttler", "data_types")
        LinkedLimitWeightPair, RateLimit = (  # noqa: N806
            data_types.LinkedLimitWeightPair,
            data_types.RateLimit,
        )

        self._throttler = throttler
        self._clock = clock
        self._sleep = sleep
        pool = pool_key_for(adapter)
        # The pause is keyed by pool: the exchange's shared budget, whatever the host link.
        self._state = _shared_state(throttler, pool)
        limit = rest_limit_for(adapter)

        host_id = getattr(adapter, "REST_HOST_RATE_LIMIT_ID", None)
        linked: list[Any] = []
        self._limit_id = f"candles-feed:{pool}"
        if host_id is None:
            logger.debug(
                "%s declares no host rate-limit pool; registering %s unlinked", pool, self._limit_id
            )
        elif _registered_limit(throttler, host_id) is None:
            logger.info(
                "Host throttler has no rate limit %r; registering %s unlinked",
                host_id,
                self._limit_id,
            )
        else:
            weight = int(getattr(adapter, "REST_HOST_RATE_LIMIT_WEIGHT", 1))
            linked.append(LinkedLimitWeightPair(host_id, weight))
            self._limit_id = f"candles-feed:{pool}:{host_id}"

        requested = RateLimit(
            limit_id=self._limit_id,
            limit=limit.max_requests,
            time_interval=limit.period_seconds,
            linked_limits=linked,
        )
        existing = _registered_limit(throttler, self._limit_id)
        if existing is not None:
            _check_same_limit(throttler, pool, existing, requested, _owner_name(adapter))
        throttler.add_rate_limits([requested])  # type: ignore[attr-defined]

    @property
    def limit_id(self) -> str:
        """Id of the rate limit this bridge registered on the throttler."""
        return self._limit_id

    @classmethod
    def from_connector(cls, connector: Any, adapter: Any) -> "ConnectorThrottlerBridge | None":
        """Build a bridge from a connector's public ``throttler``.

        :param connector: A hummingbot connector (or any object with a ``throttler``)
        :param adapter: Adapter instance or class the feed will use
        :return: The bridge, or None when the connector has no throttler (e.g. Gateway
            connectors) or hummingbot is not importable
        """
        throttler = getattr(connector, "throttler", None)
        if throttler is None:
            return None
        try:
            return cls(throttler, adapter)
        except ImportError:
            logger.debug("hummingbot is not importable; not sharing the connector's budget")
            return None

    @property
    def backoff(self) -> BackoffPolicy:
        """Backoff policy shared by all bridges on this throttler and limit id."""
        return self._state.backoff

    def pause(self, seconds: float) -> None:
        """Block ``acquire`` on every bridge sharing this throttler and limit id.

        This only stops the feeds; it cannot stop the host connector's own requests.
        """
        self._state.deadline = max(self._state.deadline, self._clock() + max(0.0, seconds))

    def is_paused(self) -> bool:
        """Whether a pause is currently active on this limit."""
        return self._state.deadline > self._clock()

    async def acquire(self) -> None:
        """Wait out any pause, then for capacity on the feed's limit (and linked host pool)."""
        await wait_out_deadline(lambda: self._state.deadline, self._clock, self._sleep)
        async with self._throttler.execute_task(self._limit_id):
            pass
