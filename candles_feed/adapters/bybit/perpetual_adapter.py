"""
Bybit perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.bybit.base_adapter import BybitBaseAdapter
from candles_feed.adapters.bybit.constants import (
    CANDLES_ENDPOINT,
    PERP_WSS_URL,
    REST_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("bybit_perpetual")
class BybitPerpetualAdapter(BybitBaseAdapter):
    """Bybit perpetual exchange adapter."""

    @staticmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    @staticmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return PERP_WSS_URL

    def get_category_param(self) -> str:
        """Get the category parameter for the market type.

        :return: Category parameter string
        """
        return "linear"