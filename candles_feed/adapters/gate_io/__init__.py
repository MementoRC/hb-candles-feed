"""
Gate.io exchange adapter package.
"""

from candles_feed.adapters.gate_io.gate_io_base_adapter import GateIoBaseAdapter
from candles_feed.adapters.gate_io.gate_io_perpetual_adapter import GateIoPerpetualAdapter
from candles_feed.adapters.gate_io.gate_io_spot_adapter import GateIoSpotAdapter

__all__ = ["GateIoBaseAdapter", "GateIoPerpetualAdapter", "GateIoSpotAdapter"]
