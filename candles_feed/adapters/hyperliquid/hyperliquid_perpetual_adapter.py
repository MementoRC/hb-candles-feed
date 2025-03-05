"""
HyperLiquid perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.hyperliquid.constants import (
    PERP_REST_URL,
    PERP_WSS_URL,
)
from candles_feed.adapters.hyperliquid.hyperliquid_base_adapter import HyperliquidBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("hyperliquid_perpetual")
class HyperliquidPerpetualAdapter(HyperliquidBaseAdapter):
    """HyperLiquid perpetual exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return PERP_REST_URL

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return PERP_WSS_URL