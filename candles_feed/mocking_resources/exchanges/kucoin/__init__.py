"""
KuCoin plugins for the mock exchange server.
"""

from candles_feed.mocking_resources.exchanges.kucoin.spot_plugin import KucoinSpotPlugin
from candles_feed.mocking_resources.exchanges.kucoin.perpetual_plugin import KucoinPerpetualPlugin

__all__ = ["KucoinSpotPlugin", "KucoinPerpetualPlugin"]