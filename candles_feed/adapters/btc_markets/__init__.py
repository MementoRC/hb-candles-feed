"""
BTC Markets exchange adapter package.
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
from .spot_adapter import BTCMarketsSpotAdapter

__all__ = [
    "BTCMarketsSpotAdapter",
    "CANDLES_ENDPOINT",
    "INTERVAL_TO_EXCHANGE_FORMAT",
    "INTERVALS",
    "MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST",
    "REST_URL",
    "WS_INTERVALS",
    "WSS_URL",
]
