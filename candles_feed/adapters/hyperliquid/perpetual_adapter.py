"""
HyperLiquid perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.hyperliquid.constants import (
    PERP_WSS_URL,
    REST_URL,
)
from candles_feed.adapters.hyperliquid.base_adapter import HyperliquidBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("hyperliquid_perpetual")
class HyperliquidPerpetualAdapter(HyperliquidBaseAdapter):
    """HyperLiquid perpetual exchange adapter."""

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
        return PERP_WSS_URL