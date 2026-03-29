"""
Bitmart exchange adapter package.
"""

from .constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_REST,
    INTERVAL_TO_EXCHANGE_WS,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from .perpetual_adapter import BitmartPerpetualAdapter

__all__ = [
    # Adapters
    "BitmartPerpetualAdapter",
    # Constants
    "CANDLES_ENDPOINT",
    "INTERVAL_TO_EXCHANGE_REST",
    "INTERVAL_TO_EXCHANGE_WS",
    "INTERVALS",
    "MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST",
    "REST_URL",
    "WSS_URL",
    "WS_INTERVALS",
]
