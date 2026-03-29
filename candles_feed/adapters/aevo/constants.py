"""
Common constants for the Aevo adapter.
"""

# API URLs and endpoints
REST_URL = "https://api.aevo.xyz"
CANDLES_ENDPOINT = "/mark-history"
WSS_URL = "wss://ws.aevo.xyz"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 200

# Intervals mapping: interval name -> seconds
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
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
}

# Aevo REST API expects resolution as number of seconds
# Maps interval name to its resolution value in seconds (same as INTERVALS)
INTERVAL_TO_EXCHANGE: dict[str, int] = dict(INTERVALS)

# Websocket supported intervals
WS_INTERVALS: list[str] = list(INTERVALS.keys())
