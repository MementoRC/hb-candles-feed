"""
Constants for the Evedex perpetual adapter.
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
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
    "1M": 2592000,
}

# Evedex uses the same interval codes as our standard intervals
INTERVAL_TO_EXCHANGE_FORMAT: dict[str, str] = {k: k for k in INTERVALS}

MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Candles are served by the market-data host; instruments by the exchange host.
MARKET_DATA_REST_URL = "https://market-data-api.evedex.com"
EXCHANGE_REST_URL = "https://exchange-api.evedex.com"

INSTRUMENTS_ENDPOINT = "/api/market/instrument"
CANDLES_ENDPOINT = "/api/history/{instrument}/list"

# Timestamps at or above this many "units" are nanoseconds
NANOSECOND_TIMESTAMP_THRESHOLD = 1e17
