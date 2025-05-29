"""
Kraken exchange adapter package.
"""

from .constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    WS_INTERVALS,
)
from .spot_adapter import KrakenSpotAdapter

__all__ = [
    # Adapters
    "KrakenSpotAdapter",
    # Constants
    "SPOT_CANDLES_ENDPOINT",
    "SPOT_REST_URL",
    "SPOT_WSS_URL",
    "INTERVAL_TO_EXCHANGE_FORMAT",
    "INTERVALS",
    "MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST",
    "WS_INTERVALS",
]
