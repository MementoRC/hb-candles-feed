"""
Kraken spot exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.rate_limiter import RestRateLimit

from .base_adapter import KrakenBaseAdapter
from .constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)


@ExchangeRegistry.register("kraken_spot")
class KrakenSpotAdapter(KrakenBaseAdapter):
    """Kraken spot exchange adapter."""

    # hummingbot/data_feed/candles_feed/kraken_spot_candles/constants.py:34-36,40-43 — public endpoint pool 1 req/1s, OHLC linked weight 1
    REST_RATE_LIMIT = RestRateLimit(max_requests=1, period_seconds=1)

    @staticmethod
    @override
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    @override
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return SPOT_WSS_URL
