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

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert "ETH-USDC" to Lighter's "ETH/USDC"."""
        return trading_pair.replace("-", "/").upper()
