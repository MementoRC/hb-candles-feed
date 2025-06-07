"""
Hyperliquid spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import HyperliquidBaseAdapter
from .constants import (
    SPOT_REST_URL,
    SPOT_WSS_URL,
)


@ExchangeRegistry.register("hyperliquid_spot")
class HyperliquidSpotAdapter(HyperliquidBaseAdapter):
    """Hyperliquid spot exchange adapter."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return SPOT_REST_URL

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return SPOT_WSS_URL
