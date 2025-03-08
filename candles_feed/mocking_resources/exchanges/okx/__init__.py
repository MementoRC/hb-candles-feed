
"""
OKX plugins for the mock exchange server.
"""

from candles_feed.mocking_resources.exchanges.okx.spot_plugin import OKXSpotPlugin
from candles_feed.mocking_resources.exchanges.okx.perpetual_plugin import OKXPerpetualPlugin

__all__ = ["OKXSpotPlugin", "OKXPerpetualPlugin"]
