"""
Binance perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.binance.binance_base_adapter import BinanceBaseAdapter
from candles_feed.adapters.binance.constants import (
    PERP_REST_URL,
    PERP_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("binance_perpetual")
class BinancePerpetualAdapter(BinanceBaseAdapter):
    """Binance perpetual exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        return PERP_REST_URL

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        return PERP_WSS_URL
