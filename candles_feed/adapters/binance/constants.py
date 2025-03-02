"""
Common constants for Binance adapters.
"""

from typing import Dict

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
    "1M": 2592000
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# API URLs - Spot
SPOT_REST_BASE_URL = "https://api.binance.com"
SPOT_CANDLES_ENDPOINT = "/api/v3/klines"
SPOT_REST_URL = f"{SPOT_REST_BASE_URL}{SPOT_CANDLES_ENDPOINT}"
SPOT_WSS_URL = "wss://stream.binance.com:9443/ws"

# API URLs - Perpetual
PERP_REST_BASE_URL = "https://fapi.binance.com"
PERP_CANDLES_ENDPOINT = "/fapi/v1/klines" 
PERP_REST_URL = f"{PERP_REST_BASE_URL}{PERP_CANDLES_ENDPOINT}"
PERP_WSS_URL = "wss://fstream.binance.com/ws"