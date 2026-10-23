"""
Coinbase Advanced Trade adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.rate_limiter import RestRateLimit

from .base_adapter import CoinbaseAdvancedTradeBaseAdapter
from .constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)


@ExchangeRegistry.register("coinbase_advanced_trade")
class CoinbaseAdvancedTradeSpotAdapter(CoinbaseAdvancedTradeBaseAdapter):
    """Coinbase Advanced Trade exchange adapter."""

    # hummingbot/connector/exchange/coinbase_advanced_trade/coinbase_advanced_trade_constants.py:92,128,209 — candles in PUBLIC_REST_ENDPOINTS, public REST 10 req/1s
    REST_RATE_LIMIT = RestRateLimit(max_requests=10, period_seconds=1)

    @staticmethod
    @override
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL template (requires formatting with product_id)
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    @override
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return SPOT_WSS_URL
