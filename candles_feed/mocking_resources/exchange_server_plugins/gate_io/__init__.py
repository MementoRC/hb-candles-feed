"""
Gate.io exchange plugin for the mock exchange server.
"""

from .perpetual_plugin import GateIoPerpetualPlugin
from .spot_plugin import GateIoSpotPlugin

__all__ = [
    "GateIoSpotPlugin",
    "GateIoPerpetualPlugin",
]
