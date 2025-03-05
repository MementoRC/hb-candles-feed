"""
Constants for the AscendEx spot adapter.
"""

from typing import Dict

# API URLs
REST_URL = "https://ascendex.com/api/pro/v1/"
WSS_URL = "wss://ascendex.com:443/api/pro/v1/websocket-for-hummingbot-liq-mining/stream"

# API endpoints
CANDLES_ENDPOINT = "barhist"
HEALTH_CHECK_ENDPOINT = "risk-limit-info"

# WebSocket
SUB_ENDPOINT_NAME = "sub"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 500

# Intervals mapping: interval name -> seconds and AscendEx format
INTERVALS: dict[str, int] = {
    "1m": 60,
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

# AscendEx interval formats
INTERVAL_TO_ASCENDEX_FORMAT = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "2h": "120",
    "4h": "240",
    "6h": "360",
    "12h": "720",
    "1d": "1d",
    "1w": "1w",
    "1M": "1m",
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())
