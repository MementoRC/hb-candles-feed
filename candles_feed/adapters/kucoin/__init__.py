"""
KuCoin exchange adapter package.
"""

from candles_feed.adapters.kucoin.kucoin_base_adapter import KuCoinBaseAdapter
from candles_feed.adapters.kucoin.kucoin_perpetual_adapter import KuCoinPerpetualAdapter
from candles_feed.adapters.kucoin.kucoin_spot_adapter import KuCoinSpotAdapter

__all__ = ["KuCoinBaseAdapter", "KuCoinPerpetualAdapter", "KuCoinSpotAdapter"]
