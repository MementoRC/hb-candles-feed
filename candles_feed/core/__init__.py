"""
Core components for the candles_feed_v2 package.
"""

from .candle_data import CandleData
from .network_client import cleanup_unclosed_sessions
from .network_config import EndpointType, NetworkConfig, NetworkEnvironment
from .protocols import (
    AsyncThrottlerProtocol,
    CollectionStrategy,
    Logger,
    NetworkClientProtocol,
    WSAssistant,
)

__all__ = [
    "CandleData",
    "cleanup_unclosed_sessions",
    "NetworkConfig",
    "EndpointType",
    "NetworkEnvironment",
    "WSAssistant",
    "CollectionStrategy",
    "Logger",
    "NetworkClientProtocol",
    "AsyncThrottlerProtocol",
]
