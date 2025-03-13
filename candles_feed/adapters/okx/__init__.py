"""
OKX exchange adapter package.
"""

from .constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)

from .perpetual_adapter import OKXPerpetualAdapter
from .spot_adapter import OKXSpotAdapter

__all__ = [
    # Adapters
    "OKXPerpetualAdapter", 
    "OKXSpotAdapter",
    
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
