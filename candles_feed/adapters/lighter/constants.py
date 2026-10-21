"""
Common constants for Lighter adapters (values copied from the upstream candles feed).
"""

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {
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

# Lighter uses the same resolution codes as our standard intervals
INTERVAL_TO_EXCHANGE_FORMAT: dict[str, str] = {k: k for k in INTERVALS}

MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Mainnet REST (Lighter has no websocket candle stream)
MAINNET_BASE_URL = "https://mainnet.zklighter.elliot.ai"

CANDLES_PATH_URL = "/api/v1/candles"
ORDER_BOOK_DETAILS_PATH_URL = "/api/v1/orderBookDetails"
