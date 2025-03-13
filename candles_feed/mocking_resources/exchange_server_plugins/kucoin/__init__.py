"""
KuCoin plugins for the mock exchange server.
"""

from .spot_plugin import KucoinSpotPlugin
from .perpetual_plugin import KucoinPerpetualPlugin

__all__ = ["KucoinSpotPlugin", "KucoinPerpetualPlugin"]