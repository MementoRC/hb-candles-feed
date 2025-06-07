"""
Mock adapter resources for testing.

This package contains mock adapter implementations for testing
different patterns of the Candle Feed framework.
"""

from .async_mocked_adapter import AsyncMockedAdapter
from .constants import (
    DEFAULT_CANDLES_LIMIT,
    INTERVALS,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
    REST_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from .hybrid_mocked_adapter import HybridMockedAdapter
from .mocked_adapter import MockedAdapter
from .sync_mocked_adapter import SyncMockedAdapter

__all__ = [
    # Constants
    "SPOT_REST_URL",
    "PERPETUAL_REST_URL",
    "REST_CANDLES_ENDPOINT",
    "SPOT_WSS_URL",
    "PERPETUAL_WSS_URL",
    "INTERVALS",
    "DEFAULT_CANDLES_LIMIT",
    # Adapters
    "MockedAdapter",
    "SyncMockedAdapter",
    "AsyncMockedAdapter",
    "HybridMockedAdapter",
]
