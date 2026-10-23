"""
Lighter spot exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import LighterBaseAdapter


@ExchangeRegistry.register("lighter_spot")
class LighterSpotAdapter(LighterBaseAdapter):
    """Lighter spot exchange adapter."""

    # Spot markets live under "spot_order_book_details"; "order_book_details" holds perpetuals.
    MARKETS_KEY = "spot_order_book_details"

    # hummingbot/data_feed/candles_feed/lighter_spot_candles/constants.py:44 links candles to lighter_all at weight 300 (pool also in connector/exchange/lighter/lighter_constants.py:161)
    # Pool ids differ between spot and perpetual, so each variant declares its own.
    REST_HOST_RATE_LIMIT_ID = "lighter_all"
    REST_HOST_RATE_LIMIT_WEIGHT = 300

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert "ETH-USDC" to Lighter's "ETH/USDC"."""
        return trading_pair.replace("-", "/").upper()
