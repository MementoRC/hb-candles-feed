"""
Pacifica exchange adapter package.
"""

from .constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from .perpetual_adapter import PacificaPerpetualAdapter

__all__ = [
    "PacificaPerpetualAdapter",
    "CANDLES_ENDPOINT",
    "INTERVAL_TO_EXCHANGE_FORMAT",
    "INTERVALS",
    "MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST",
    "REST_URL",
    "WS_INTERVALS",
    "WSS_URL",
]
