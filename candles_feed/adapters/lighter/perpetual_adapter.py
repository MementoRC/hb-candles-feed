"""
Lighter perpetual exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import LighterBaseAdapter


@ExchangeRegistry.register("lighter_perpetual")
class LighterPerpetualAdapter(LighterBaseAdapter):
    """Lighter perpetual exchange adapter."""

    MARKETS_KEY = "order_book_details"

    # hummingbot/data_feed/candles_feed/lighter_perpetual_candles/constants.py:39 links candles to lighter_perpetual_all at weight 300 (pool also in connector/derivative/lighter_perpetual/lighter_perpetual_constants.py:160)
    # Pool ids differ between spot and perpetual, so each variant declares its own.
    REST_HOST_RATE_LIMIT_ID = "lighter_perpetual_all"
    REST_HOST_RATE_LIMIT_WEIGHT = 300

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert "ETH-USDC" to Lighter's perpetual symbol "ETH" (base asset only)."""
        return trading_pair.split("-")[0].upper()
