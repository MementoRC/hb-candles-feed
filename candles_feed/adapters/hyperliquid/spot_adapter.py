"""
Hyperliquid spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.hyperliquid.constants import (
    REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.adapters.hyperliquid.base_adapter import HyperliquidBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("hyperliquid_spot")
class HyperliquidSpotAdapter(HyperliquidBaseAdapter):
    """Hyperliquid spot exchange adapter."""

    @staticmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return REST_URL

    @staticmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return SPOT_WSS_URL