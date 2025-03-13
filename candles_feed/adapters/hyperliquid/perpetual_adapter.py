"""
HyperLiquid perpetual exchange adapter for the Candle Feed framework.
"""

from .constants import (
    PERPETUAL_WSS_URL,
    PERPETUAL_REST_URL,
    PERPETUAL_CANDLES_ENDPOINT,
)
from .base_adapter import HyperliquidBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("hyperliquid_perpetual")
class HyperliquidPerpetualAdapter(HyperliquidBaseAdapter):
    """HyperLiquid perpetual exchange adapter."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return PERPETUAL_REST_URL

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return PERPETUAL_WSS_URL