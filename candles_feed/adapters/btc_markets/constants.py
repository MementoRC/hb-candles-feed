"""
Common constants for BTC Markets adapters.
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
    "3h": 10800,
    "4h": 14400,
    "6h": 21600,
    "1d": 86400,
    "1w": 604800,
}

# BTC Markets interval format matches our standard interval names
INTERVAL_TO_EXCHANGE_FORMAT: dict[str, str] = {k: k for k in INTERVALS}

# BTC Markets has no WebSocket support for candles
WS_INTERVALS: list[str] = []

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# API URLs and endpoints
REST_URL = "https://api.btcmarkets.net"
CANDLES_ENDPOINT = "/v3/markets/{market_id}/candles"

# BTC Markets has no WebSocket API for candles
WSS_URL: str | None = None
