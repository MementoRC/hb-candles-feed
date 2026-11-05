"""
Bitget plugins for the mock exchange server.
"""

from .perpetual_plugin import BitgetPerpetualPlugin
from .spot_plugin import BitgetSpotPlugin

__all__ = ["BitgetPerpetualPlugin", "BitgetSpotPlugin"]
