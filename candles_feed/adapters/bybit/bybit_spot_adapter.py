"""
Bybit spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.bybit.bybit_base_adapter import BybitBaseAdapter
from candles_feed.adapters.bybit.constants import SPOT_WSS_URL, WSS_URL
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("bybit_spot")
class BybitSpotAdapter(BybitBaseAdapter):
    """Bybit spot exchange adapter."""

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        # Use old constants for compatibility with tests
        return WSS_URL

    def get_category_param(self) -> str:
        """Get the category parameter for the market type.

        :return: Category parameter string
        """
        return "spot"