"""
Common constants for Backpack adapters.
"""

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

# Backpack uses "1month" instead of "1M" for the monthly interval.
INTERVAL_TO_EXCHANGE_FORMAT: dict[str, str] = {k: k for k in INTERVALS}
INTERVAL_TO_EXCHANGE_FORMAT["1M"] = "1month"

# Websocket supported intervals
WS_INTERVALS: list[str] = list(INTERVALS.keys())

# API limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# API URLs and endpoints (spot and perpetual share the same host and endpoints)
REST_URL = "https://api.backpack.exchange"
CANDLES_ENDPOINT = "/api/v1/klines"
HEALTH_CHECK_ENDPOINT = "/api/v1/status"
WSS_URL = "wss://ws.backpack.exchange"
