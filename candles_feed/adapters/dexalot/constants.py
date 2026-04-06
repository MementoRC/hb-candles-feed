"""
Common constants for Dexalot adapters.
"""

# API URLs and endpoints
REST_URL = "https://api.dexalot.com/privapi"
CANDLES_ENDPOINT = "/trading/candlechart"
WSS_URL = "wss://api.dexalot.com/api/ws"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

# Dexalot interval formats - maps standard interval names to Dexalot exchange format
INTERVAL_TO_EXCHANGE_FORMAT: dict[str, str] = {
    "5m": "M5",
    "15m": "M15",
    "30m": "M30",
    "1h": "H1",
    "4h": "H4",
    "1d": "D1",
}

# Websocket supported intervals
WS_INTERVALS: list[str] = list(INTERVALS.keys())
