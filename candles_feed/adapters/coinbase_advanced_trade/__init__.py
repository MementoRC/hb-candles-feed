"""
Coinbase Advanced Trade exchange adapter package.
"""

from .constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)

from .spot_adapter import CoinbaseAdvancedTradeSpotAdapter

__all__ = [
    # Adapters
    "CoinbaseAdvancedTradeSpotAdapter",
    
    # Constants
    "SPOT_CANDLES_ENDPOINT",
    "SPOT_REST_URL",
    "SPOT_WSS_URL",
    "INTERVAL_TO_EXCHANGE_FORMAT",
    "INTERVALS",
    "MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST",
    "WS_INTERVALS",
]
