"""
MEXC exchange adapter package.
"""

from .constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    WS_INTERVALS,
)
from .perpetual_adapter import MEXCPerpetualAdapter
from .spot_adapter import MEXCSpotAdapter

__all__ = [
    # Adapters
    "MEXCPerpetualAdapter",
    "MEXCSpotAdapter",
    # Constants
    "SPOT_CANDLES_ENDPOINT",
    "SPOT_REST_URL",
    "SPOT_WSS_URL",
    "PERPETUAL_CANDLES_ENDPOINT",
    "PERPETUAL_REST_URL",
    "PERPETUAL_WSS_URL",
    "INTERVAL_TO_EXCHANGE_FORMAT",
    "INTERVALS",
    "MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST",
    "WS_INTERVALS",
]
