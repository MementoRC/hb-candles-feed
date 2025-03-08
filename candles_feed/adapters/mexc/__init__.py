"""
MEXC exchange adapter package.
"""

from candles_feed.adapters.mexc.base_adapter import MEXCBaseAdapter
from candles_feed.adapters.mexc.perpetual_adapter import MEXCPerpetualAdapter
from candles_feed.adapters.mexc.spot_adapter import MEXCSpotAdapter

__all__ = ["MEXCBaseAdapter", "MEXCPerpetualAdapter", "MEXCSpotAdapter"]
