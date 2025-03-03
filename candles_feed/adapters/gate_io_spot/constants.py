"""
Constants for the Gate.io spot adapter.
"""

from typing import Dict

# API URLs
REST_URL = "https://api.gateio.ws/api/v4/spot"
WSS_URL = "wss://api.gateio.ws/ws/v4/"

# API endpoints
CANDLES_ENDPOINT = "/candlesticks"
HEALTH_CHECK_ENDPOINT = "/time"

# WebSocket
SUB_ENDPOINT_NAME = "subscribe"
CHANNEL_NAME = "spot.candlesticks"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {
    "10s": 10,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "8h": 28800,
    "1d": 86400,
    "7d": 604800,
}

# Gate.io interval formats mapping
INTERVAL_TO_GATE_IO_FORMAT = {
    "10s": "10s",
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "8h": "8h",
    "1d": "1d",
    "7d": "7d",
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())
