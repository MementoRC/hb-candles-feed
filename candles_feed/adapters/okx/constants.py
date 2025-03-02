"""
Common constants for OKX adapters.
"""

from typing import Dict

# API URLs - Common
REST_BASE_URL = "https://www.okx.com"
WSS_BASE_URL = "wss://ws.okx.com:8443/ws/v5/public"

# API URLs - Spot
SPOT_REST_URL = REST_BASE_URL
SPOT_CANDLES_ENDPOINT = "/api/v5/market/candles"
SPOT_WSS_URL = WSS_BASE_URL

# API URLs - Perpetual
PERP_REST_URL = REST_BASE_URL
PERP_CANDLES_ENDPOINT = "/api/v5/market/candles"
PERP_WSS_URL = WSS_BASE_URL

# API endpoints
STATUS_ENDPOINT = "/api/v5/system/status"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 300

# Intervals mapping: interval name -> seconds and OKX format
INTERVALS: Dict[str, int] = {
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
    "1M": 2592000
}

# OKX interval formats
INTERVAL_TO_OKX_FORMAT = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "2h": "2H",
    "4h": "4H",
    "6h": "6H",
    "12h": "12H",
    "1d": "1D",
    "1w": "1W",
    "1M": "1M"
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())