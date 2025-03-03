"""
Constants for the Binance spot adapter.
"""

from typing import Dict

# API URLs
REST_URL = "https://api.binance.com/api/v3/klines"
WSS_URL = "wss://stream.binance.com:9443/ws"
HEALTH_CHECK_URL = "https://api.binance.com/api/v3/ping"

# API endpoints
CANDLES_ENDPOINT = "/api/v3/klines"
HEALTH_CHECK_ENDPOINT = "/api/v3/ping"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Intervals mapping: interval name -> seconds
INTERVALS: Dict[str, int] = {
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
