"""Hummingbot compatibility layer for candles_feed.

Provides drop-in replacement types and protocols matching hummingbot's
MarketDataProvider interface.
"""

from candles_feed.hb_compat.adapter import CandlesBaseAdapter
from candles_feed.hb_compat.data_types import (
    CandlesConfig,
    HistoricalCandlesConfig,
    UnsupportedConnectorException,
)
from candles_feed.hb_compat.protocols import CandlesBaseProtocol

__all__ = [
    "CandlesBaseAdapter",
    "CandlesBaseProtocol",
    "CandlesConfig",
    "HistoricalCandlesConfig",
    "UnsupportedConnectorException",
]
