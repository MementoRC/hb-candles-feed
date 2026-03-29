"""
Bitget exchange adapter package.
"""

from .constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_INTERVAL_TO_EXCHANGE,
    PERPETUAL_REST_URL,
    SPOT_CANDLES_ENDPOINT,
    SPOT_INTERVAL_TO_EXCHANGE,
    SPOT_REST_URL,
    WS_INTERVAL_TO_EXCHANGE,
    WS_INTERVALS,
    WSS_URL,
)
from .perpetual_adapter import BitgetPerpetualAdapter
from .spot_adapter import BitgetSpotAdapter

__all__ = [
    "BitgetSpotAdapter",
    "BitgetPerpetualAdapter",
    "INTERVALS",
    "MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST",
    "PERPETUAL_CANDLES_ENDPOINT",
    "PERPETUAL_INTERVAL_TO_EXCHANGE",
    "PERPETUAL_REST_URL",
    "SPOT_CANDLES_ENDPOINT",
    "SPOT_INTERVAL_TO_EXCHANGE",
    "SPOT_REST_URL",
    "WS_INTERVAL_TO_EXCHANGE",
    "WS_INTERVALS",
    "WSS_URL",
]
