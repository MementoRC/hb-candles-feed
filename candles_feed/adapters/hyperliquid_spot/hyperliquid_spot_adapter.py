"""
Hyperliquid spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.hyperliquid.constants import (
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.adapters.hyperliquid.hyperliquid_base_adapter import HyperliquidBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("hyperliquid_spot")
class HyperliquidSpotAdapter(HyperliquidBaseAdapter):
    """Hyperliquid spot exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        return SPOT_REST_URL

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        return SPOT_WSS_URL
