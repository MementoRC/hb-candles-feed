"""
Constants for the Bybit perpetual adapter.
"""

from typing import Dict

# API URLs
REST_URL = "https://api.bybit.com"
WSS_URL = "wss://stream.bybit.com/v5/public/linear"

# API endpoints
CANDLES_ENDPOINT = "/v5/market/kline"
SERVER_TIME_ENDPOINT = "/v5/market/time"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Intervals mapping: interval name -> seconds and Bybit format
INTERVALS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "12h": 43200,
    "1d": 86400,
    "1w": 604800,
    "1M": 2592000,
}

# Bybit interval formats
INTERVAL_TO_BYBIT_FORMAT = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "2h": "120",
    "4h": "240",
    "6h": "360",
    "12h": "720",
    "1d": "D",
    "1w": "W",
    "1M": "M",
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())
