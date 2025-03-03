"""
Bybit spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.bybit.bybit_base_adapter import BybitBaseAdapter
from candles_feed.adapters.bybit.constants import SPOT_WSS_URL
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("bybit_spot")
class BybitSpotAdapter(BybitBaseAdapter):
    """Bybit spot exchange adapter."""

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        return SPOT_WSS_URL

    def get_category_param(self) -> str:
        """Get the category parameter for the market type.

        Returns:
            Category parameter string
        """
        return "spot"
