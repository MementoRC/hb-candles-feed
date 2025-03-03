"""
Constants for the Binance perpetual adapter.
"""

from typing import Dict

# API URLs
REST_URL = "https://fapi.binance.com/fapi/v1/klines"
WSS_URL = "wss://fstream.binance.com/ws"
HEALTH_CHECK_URL = "https://fapi.binance.com/fapi/v1/ping"

# API endpoints
CANDLES_ENDPOINT = "/fapi/v1/klines"
HEALTH_CHECK_ENDPOINT = "/fapi/v1/ping"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {
    "1s": 1,
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
    "1M": 2592000,
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())
