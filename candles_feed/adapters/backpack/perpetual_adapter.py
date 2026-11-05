"""
Backpack perpetual exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import BackpackBaseAdapter

# Perpetual market symbols carry this suffix (e.g. BTC_USDC_PERP)
PERPETUAL_SYMBOL_SUFFIX = "_PERP"


@ExchangeRegistry.register("backpack_perpetual")
class BackpackPerpetualAdapter(BackpackBaseAdapter):
    """Backpack perpetual exchange adapter."""

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert "BTC-USDC" to Backpack's "BTC_USDC_PERP".

        :param trading_pair: Trading pair in standard format
        :returns: Backpack perpetual symbol
        """
        return f"{trading_pair.replace('-', '_')}{PERPETUAL_SYMBOL_SUFFIX}"
