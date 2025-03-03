"""
Common constants for HyperLiquid adapters.
"""

from typing import Dict

# API URLs - Common
REST_BASE_URL = "https://api.hyperliquid.xyz/info"
WSS_BASE_URL = "wss://api.hyperliquid.xyz/ws"

# API URLs - Spot
SPOT_REST_URL = REST_BASE_URL
SPOT_WSS_URL = WSS_BASE_URL

# API URLs - Perpetual
PERP_REST_URL = REST_BASE_URL
PERP_WSS_URL = WSS_BASE_URL

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 500

# Intervals mapping: interval name -> seconds
INTERVALS: Dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "12h": 43200,
    "1d": 86400,
    "1w": 604800,
}

# HyperLiquid interval formats mapping
INTERVAL_TO_HYPERLIQUID_FORMAT = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
    "12h": "720",
    "1d": "D",
    "1w": "W",
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())

# Channel names
CHANNEL_NAME = "candles"
