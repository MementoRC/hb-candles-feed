"""
Common constants for Gate.io adapters.
"""

from typing import Dict

# API URLs - Common
REST_BASE_URL = "https://api.gateio.ws/api/v4"
WSS_BASE_URL = "wss://api.gateio.ws/ws/v4/"

# API URLs - Spot
SPOT_CANDLES_ENDPOINT = "/spot/candlesticks"
SPOT_CHANNEL_NAME = "spot.candlesticks"
SPOT_REST_URL = f"{REST_BASE_URL}{SPOT_CANDLES_ENDPOINT}"
SPOT_WSS_URL = WSS_BASE_URL

# API URLs - Perpetual
PERP_CANDLES_ENDPOINT = "/futures/usdt/candlesticks"
PERP_CHANNEL_NAME = "futures.candlesticks"
PERP_REST_URL = f"{REST_BASE_URL}{PERP_CANDLES_ENDPOINT}"
PERP_WSS_URL = WSS_BASE_URL

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Intervals mapping: interval name -> seconds
INTERVALS: Dict[str, int] = {
    "10s": 10,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "8h": 28800,
    "1d": 86400,
    "7d": 604800
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
    "7d": "7d"
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())