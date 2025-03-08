"""
Gate.io exchange plugin for the mock exchange server.
"""

from candles_feed.mocking_resources.exchanges.gate_io.spot_plugin import GateIoSpotPlugin
from candles_feed.mocking_resources.exchanges.gate_io.perpetual_plugin import GateIoPerpetualPlugin

__all__ = [
    "GateIoSpotPlugin",
    "GateIoPerpetualPlugin",
]