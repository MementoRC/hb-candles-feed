"""
Gate.io exchange adapter package.
"""

from candles_feed.adapters.gate_io.base_adapter import GateIoBaseAdapter
from candles_feed.adapters.gate_io.perpetual_adapter import GateIoPerpetualAdapter
from candles_feed.adapters.gate_io.spot_adapter import GateIoSpotAdapter

__all__ = ["GateIoBaseAdapter", "GateIoPerpetualAdapter", "GateIoSpotAdapter"]
