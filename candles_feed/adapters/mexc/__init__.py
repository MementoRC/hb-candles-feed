"""
MEXC exchange adapter package.
"""

from candles_feed.adapters.mexc.mexc_base_adapter import MEXCBaseAdapter
from candles_feed.adapters.mexc.mexc_perpetual_adapter import MEXCPerpetualAdapter
from candles_feed.adapters.mexc.mexc_spot_adapter import MEXCSpotAdapter

__all__ = ["MEXCBaseAdapter", "MEXCPerpetualAdapter", "MEXCSpotAdapter"]
