"""Bridge from a hummingbot connector's throttler to the feed's REST rate limiter.

Lets a feed created next to a connector (``CandlesFactory.get_candle(config, connector)``)
spend from the connector's shared rate-limit budget, so the feed's klines requests and the
connector's own requests are paced together instead of racing for the exchange's limit.
"""

import logging
from typing import Any

from candles_feed.core.protocols import AsyncThrottlerProtocol
from candles_feed.core.rate_limiter import pool_key_for, rest_limit_for

logger = logging.getLogger(__name__)


class ConnectorThrottlerBridge:
    """``RestRateLimiterProtocol`` implementation backed by a hummingbot throttler.

    Registers one rate limit ``candles-feed:<pool>`` on the throttler, sized from the
    adapter's ``REST_RATE_LIMIT``. When the adapter names a host pool
    (``REST_HOST_RATE_LIMIT_ID``) that the throttler already defines, the limit is linked
    to it with ``REST_HOST_RATE_LIMIT_WEIGHT``, so each request also consumes the host
    budget. Otherwise it is registered unlinked and only paces the feed itself.

    Bridges on the same throttler and pool share one limit (registration is additive).
    """

    def __init__(self, throttler: AsyncThrottlerProtocol, adapter: Any) -> None:
        # Imported here so that importing this module never requires hummingbot.
        from hummingbot.core.api_throttler.data_types import LinkedLimitWeightPair, RateLimit

        self._throttler = throttler
        pool = pool_key_for(adapter)
        self._limit_id = f"candles-feed:{pool}"
        limit = rest_limit_for(adapter)

        host_id = getattr(adapter, "REST_HOST_RATE_LIMIT_ID", None)
        linked: list[Any] = []
        if host_id is None:
            logger.debug(
                "%s declares no host rate-limit pool; registering %s unlinked", pool, self._limit_id
            )
        elif host_id not in (getattr(throttler, "_id_to_limit_map", None) or {}):
            logger.info(
                "Host throttler has no rate limit %r; registering %s unlinked",
                host_id,
                self._limit_id,
            )
        else:
            weight = int(getattr(adapter, "REST_HOST_RATE_LIMIT_WEIGHT", 1))
            linked.append(LinkedLimitWeightPair(host_id, weight))

        throttler.add_rate_limits(  # type: ignore[attr-defined]
            [
                RateLimit(
                    limit_id=self._limit_id,
                    limit=limit.max_requests,
                    time_interval=limit.period_seconds,
                    linked_limits=linked,
                )
            ]
        )

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

    async def acquire(self) -> None:
        """Wait for capacity on the feed's limit (and the linked host pool), then record it."""
        async with self._throttler.execute_task(self._limit_id):
            pass
