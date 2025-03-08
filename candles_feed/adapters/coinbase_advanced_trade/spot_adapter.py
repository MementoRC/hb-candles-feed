"""
Coinbase Advanced Trade adapter for the Candle Feed framework.
"""

from candles_feed.adapters.coinbase_advanced_trade.base_adapter import CoinbaseAdvancedTradeAdapter
from candles_feed.adapters.coinbase_advanced_trade.constants import (
    CANDLES_ENDPOINT,
    REST_URL,
    WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("coinbase_advanced_trade")
class CoinbaseAdvancedTradeSpotAdapter(CoinbaseAdvancedTradeAdapter):
    """Coinbase Advanced Trade exchange adapter."""

    @staticmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL template (requires formatting with product_id)
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    @staticmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return WSS_URL
