"""
Kraken spot exchange adapter for the Candle Feed framework.
"""

from .base_adapter import KrakenBaseAdapter
from .constants import (
    SPOT_REST_URL,
    SPOT_CANDLES_ENDPOINT,
    SPOT_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("kraken_spot")
class KrakenSpotAdapter(KrakenBaseAdapter):
    """Kraken spot exchange adapter."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return SPOT_WSS_URL
