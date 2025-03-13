"""
Gate.io exchange plugin for the mock exchange server.
"""

from .spot_plugin import GateIoSpotPlugin
from .perpetual_plugin import GateIoPerpetualPlugin

__all__ = [
    "GateIoSpotPlugin",
    "GateIoPerpetualPlugin",
]