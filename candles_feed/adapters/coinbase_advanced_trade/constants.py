"""
Constants for the Coinbase Advanced Trade adapter.
"""

# API URLs
SPOT_REST_URL = "https://api.coinbase.com"
# Public (unauthenticated) market-data endpoint; {product_id} is e.g. "BTC-USD"
SPOT_CANDLES_ENDPOINT = "/api/v3/brokerage/market/products/{product_id}/candles"
SERVER_TIME_ENDPOINT = "/api/v3/time"
PRODUCTS_ENDPOINT = "/api/v3/brokerage/products"
SPOT_WSS_URL = "wss://advanced-trade-ws.coinbase.com"

# API rate limits: the candles endpoint returns at most 350 candles per request
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 350

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "6h": 21600, "1d": 86400}

# REST `granularity` query values: interval name -> Coinbase enum
INTERVAL_TO_GRANULARITY: dict[str, str] = {
    "1m": "ONE_MINUTE",
    "5m": "FIVE_MINUTE",
    "15m": "FIFTEEN_MINUTE",
    "1h": "ONE_HOUR",
    "6h": "SIX_HOUR",
    "1d": "ONE_DAY",
}

# Coinbase Advanced Trade intervals are the same as our standard intervals
# Only needed for consistency with other adapters
INTERVAL_TO_EXCHANGE_FORMAT = {k: k for k in INTERVALS}

# The WebSocket candles channel has a fixed 5 minute interval and no granularity option
WS_INTERVALS = ["5m"]
