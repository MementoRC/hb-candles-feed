"""
Common constants for Pacifica adapters.
"""

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
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
}

# Pacifica uses the same interval format as our standard intervals
INTERVAL_TO_EXCHANGE_FORMAT: dict[str, str] = {k: k for k in INTERVALS}

# Websocket supported intervals
WS_INTERVALS: list[str] = list(INTERVALS.keys())

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# API URLs and endpoints
REST_URL = "https://api.pacifica.fi/api/v1"
CANDLES_ENDPOINT = "/kline"
WSS_URL = "wss://ws.pacifica.fi/ws"
