"""
Coinbase Advanced Trade Spot plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.coinbase_advanced_trade.spot_adapter import (
    CoinbaseAdvancedTradeSpotAdapter,
)
from candles_feed.mocking_resources.core.exchange_type import ExchangeType

from .base_plugin import CoinbaseAdvancedTradeBasePlugin


class CoinbaseAdvancedTradeSpotPlugin(CoinbaseAdvancedTradeBasePlugin):
    """
    Coinbase Advanced Trade Spot plugin for the mock exchange server.

    This plugin implements the Coinbase Advanced Trade Spot API for the mock server,
    translating between the standardized mock server format and the
    Coinbase Advanced Trade-specific formats.
    """

    def __init__(self):
        """
        Initialize the Coinbase Advanced Trade Spot plugin.
        """
        super().__init__(ExchangeType.COINBASE_ADVANCED_TRADE, CoinbaseAdvancedTradeSpotAdapter)

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Coinbase Advanced Trade Spot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/v3/brokerage/products/{product_id}/candles": ("GET", "handle_klines"),
            "/api/v3/time": ("GET", "handle_time"),
            "/api/v3/brokerage/products": ("GET", "handle_products"),
        }
