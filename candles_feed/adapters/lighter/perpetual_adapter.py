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

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert "ETH-USDC" to Lighter's perpetual symbol "ETH" (base asset only)."""
        return trading_pair.split("-")[0].upper()
