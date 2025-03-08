"""
OKX exchange adapter package.
"""

from candles_feed.adapters.okx.perpetual_adapter import OKXPerpetualAdapter
from candles_feed.adapters.okx.spot_adapter import OKXSpotAdapter

__all__ = ["OKXPerpetualAdapter", "OKXSpotAdapter"]
