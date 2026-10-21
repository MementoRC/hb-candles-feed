"""
Backpack spot exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import BackpackBaseAdapter


@ExchangeRegistry.register("backpack_spot")
class BackpackSpotAdapter(BackpackBaseAdapter):
    """Backpack spot exchange adapter."""

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert "BTC-USDC" to Backpack's "BTC_USDC".

        :param trading_pair: Trading pair in standard format
        :returns: Backpack spot symbol
        """
        return trading_pair.replace("-", "_")
