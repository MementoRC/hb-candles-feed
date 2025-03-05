"""
Binance spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.binance.binance_base_adapter import BinanceBaseAdapter
from candles_feed.adapters.binance.constants import (
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("binance_spot")
class BinanceSpotAdapter(BinanceBaseAdapter):
    """Binance spot exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return SPOT_REST_URL

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return SPOT_WSS_URL
