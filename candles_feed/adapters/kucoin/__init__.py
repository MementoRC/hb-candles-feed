"""
KuCoin exchange adapter package.
"""

from candles_feed.adapters.kucoin.perpetual_adapter import KucoinPerpetualAdapter
from candles_feed.adapters.kucoin.spot_adapter import KucoinSpotAdapter

__all__ = ["KucoinPerpetualAdapter", "KucoinSpotAdapter"]
