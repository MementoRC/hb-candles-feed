"""
Aevo exchange adapter package.
"""

from .constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from .perpetual_adapter import AevoPerpetualAdapter

__all__ = [
    # Adapters
    "AevoPerpetualAdapter",
    # Constants
    "CANDLES_ENDPOINT",
    "INTERVAL_TO_EXCHANGE",
    "INTERVALS",
    "MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST",
    "REST_URL",
    "WSS_URL",
    "WS_INTERVALS",
]
