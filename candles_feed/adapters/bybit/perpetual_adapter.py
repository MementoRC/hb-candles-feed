"""
Bybit perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.bybit.base_adapter import BybitBaseAdapter
from candles_feed.adapters.bybit.constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("bybit_perpetual")
class BybitPerpetualAdapter(BybitBaseAdapter):
    """Bybit perpetual exchange adapter."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return PERPETUAL_WSS_URL

    def get_category_param(self) -> str:
        """Get the category parameter for the market type.

        :returns: Category parameter string
        """
        return "linear"
