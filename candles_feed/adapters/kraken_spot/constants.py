"""
Constants for the Kraken spot adapter.
"""

from typing import Dict

# API URLs
REST_URL = "https://api.kraken.com"
WSS_URL = "wss://ws.kraken.com"

# API endpoints
CANDLES_ENDPOINT = "/0/public/OHLC"
TIME_ENDPOINT = "/0/public/Time"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 720

# Intervals mapping: interval name -> seconds and Kraken format
INTERVALS: Dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
    "15d": 1296000,
}

# Kraken interval formats (minutes)
INTERVAL_TO_KRAKEN_FORMAT = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
    "1w": 10080,
    "15d": 21600,
}

# Websocket supported intervals - Kraken WebSocket uses the same intervals
WS_INTERVALS = list(INTERVALS.keys())
