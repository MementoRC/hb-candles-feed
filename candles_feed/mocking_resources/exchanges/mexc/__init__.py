"""
MEXC plugins for the mock exchange server.
"""

from candles_feed.mocking_resources.exchanges.mexc.spot_plugin import MEXCSpotPlugin
from candles_feed.mocking_resources.exchanges.mexc.perpetual_plugin import MEXCPerpetualPlugin

__all__ = ["MEXCSpotPlugin", "MEXCPerpetualPlugin"]