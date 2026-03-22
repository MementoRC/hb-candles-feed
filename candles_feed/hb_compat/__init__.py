"""Hummingbot compatibility layer for candles_feed.

Provides drop-in replacement types and protocols matching hummingbot's
MarketDataProvider interface.
"""

from candles_feed.hb_compat.data_types import HistoricalCandlesConfig
from candles_feed.hb_compat.protocols import CandlesBaseProtocol

__all__ = [
    "CandlesBaseProtocol",
    "HistoricalCandlesConfig",
]
