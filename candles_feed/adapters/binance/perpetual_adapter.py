"""
Binance perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.binance.base_adapter import BinanceBaseAdapter
from candles_feed.adapters.binance.constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("binance_perpetual")
class BinancePerpetualAdapter(BinanceBaseAdapter):
    """Binance perpetual exchange adapter."""

    @staticmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"

    @staticmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return PERPETUAL_WSS_URL
