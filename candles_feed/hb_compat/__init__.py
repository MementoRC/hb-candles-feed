"""Hummingbot compatibility layer for candles_feed.

This package provides a drop-in replacement for hummingbot's candles connectors,
allowing hb-candles-feed to be used as a direct substitute.
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
