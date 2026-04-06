"""
Common constants for Bitmart adapters.
"""

# API URLs and endpoints
REST_URL = "https://api-cloud-v2.bitmart.com"
CANDLES_ENDPOINT = "/contract/public/kline"
WSS_URL = "wss://openapi-ws-v2.bitmart.com"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "12h": 43200,
    "1d": 86400,
    "1w": 604800,
}

# Interval to exchange REST format: numeric minutes
INTERVAL_TO_EXCHANGE_REST: dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "12h": 720,
    "1d": 1440,
    "1w": 10080,
}

# Interval to exchange WebSocket format
INTERVAL_TO_EXCHANGE_WS: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "2h": "2H",
    "4h": "4H",
    "12h": "12H",
    "1d": "1D",
    "1w": "1W",
}

# Websocket supported intervals
WS_INTERVALS: list[str] = list(INTERVAL_TO_EXCHANGE_WS.keys())
