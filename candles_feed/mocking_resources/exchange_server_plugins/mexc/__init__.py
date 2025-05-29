"""
MEXC plugins for the mock exchange server.
"""

from .perpetual_plugin import MEXCPerpetualPlugin
from .spot_plugin import MEXCSpotPlugin

__all__ = ["MEXCSpotPlugin", "MEXCPerpetualPlugin"]
