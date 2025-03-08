"""
Hyperliquid plugins for the mock exchange server.
"""

from candles_feed.mocking_resources.exchanges.hyperliquid.spot_plugin import HyperliquidSpotPlugin
from candles_feed.mocking_resources.exchanges.hyperliquid.perpetual_plugin import HyperliquidPerpetualPlugin

__all__ = ["HyperliquidSpotPlugin", "HyperliquidPerpetualPlugin"]