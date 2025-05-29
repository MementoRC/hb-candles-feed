
"""
OKX plugins for the mock exchange server.
"""

from .perpetual_plugin import OKXPerpetualPlugin
from .spot_plugin import OKXSpotPlugin

__all__ = ["OKXSpotPlugin", "OKXPerpetualPlugin"]
