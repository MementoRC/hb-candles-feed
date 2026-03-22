"""Hummingbot compatibility layer for hb-candles-feed.

Provides drop-in replacements for hummingbot's CandlesFactory, CandlesConfig,
and related classes. No hummingbot import required.

Usage in hummingbot fork:
    from candles_feed.hb_compat import CandlesFactory, CandlesConfig
"""

from candles_feed.hb_compat.adapter import CandlesBaseAdapter
from candles_feed.hb_compat.data_types import (
    CandlesConfig,
    HistoricalCandlesConfig,
    UnsupportedConnectorException,
)
from candles_feed.hb_compat.factory import CandlesFactory
from candles_feed.hb_compat.protocols import CandlesBaseProtocol

__all__ = [
    "CandlesBaseAdapter",
    "CandlesBaseProtocol",
    "CandlesConfig",
    "CandlesFactory",
    "HistoricalCandlesConfig",
    "UnsupportedConnectorException",
]
