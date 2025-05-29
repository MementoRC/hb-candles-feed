"""
Coinbase Advanced Trade adapter for the Candle Feed framework.
"""

from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import CoinbaseAdvancedTradeBaseAdapter
from .constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)


@ExchangeRegistry.register("coinbase_advanced_trade")
class CoinbaseAdvancedTradeSpotAdapter(CoinbaseAdvancedTradeBaseAdapter):
    """Coinbase Advanced Trade exchange adapter."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL template (requires formatting with product_id)
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return SPOT_WSS_URL
