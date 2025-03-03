"""
Constants for the Coinbase Advanced Trade adapter.
"""

from typing import Dict

# API URLs
BASE_REST_URL = "https://api.coinbase.com/api/v3/brokerage/products/{product_id}/candles"
WSS_URL = "wss://advanced-trade-ws.coinbase.com"

# API endpoints
CANDLES_ENDPOINT = "/api/v3/brokerage/products/{product_id}/candles"
SERVER_TIME_ENDPOINT = "/api/v3/time"
PRODUCTS_ENDPOINT = "/api/v3/brokerage/products"

# API rate limits
MAX_CANDLES_SIZE = 300

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "6h": 21600, "1d": 86400}

# Websocket supported intervals - Coinbase only supports certain intervals via WebSocket
WS_INTERVALS = ["1m", "5m", "15m", "1h"]
