"""
Constants for the Coinbase Advanced Trade adapter.
"""

# API URLs
REST_URL = "https://api.coinbase.com"
CANDLES_ENDPOINT = "/api/v3/brokerage/products/{product_id}/candles"
SERVER_TIME_ENDPOINT = "/api/v3/time"
PRODUCTS_ENDPOINT = "/api/v3/brokerage/products"
WSS_URL = "wss://advanced-trade-ws.coinbase.com"

# API rate limits
MAX_CANDLES_SIZE = 300

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "6h": 21600, "1d": 86400}

# Coinbase Advanced Trade intervals are the same as our standard intervals
# Only needed for consistency with other adapters
INTERVAL_TO_EXCHANGE_FORMAT = {k: k for k in INTERVALS}

# Websocket supported intervals - Coinbase only supports certain intervals via WebSocket
WS_INTERVALS = ["1m", "5m", "15m", "1h"]
