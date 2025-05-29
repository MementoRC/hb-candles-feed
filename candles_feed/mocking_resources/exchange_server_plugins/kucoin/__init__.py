"""
KuCoin plugins for the mock exchange server.
"""

from .perpetual_plugin import KucoinPerpetualPlugin
from .spot_plugin import KucoinSpotPlugin

__all__ = ["KucoinSpotPlugin", "KucoinPerpetualPlugin"]
