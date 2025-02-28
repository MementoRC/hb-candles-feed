"""
Constants for the KuCoin spot adapter.
"""

from typing import Dict

# API URLs
REST_URL = "https://api.kucoin.com"
WSS_URL = "wss://ws-api.kucoin.com"

# API endpoints
CANDLES_ENDPOINT = "/api/v1/market/candles"
TICKER_ENDPOINT = "/api/v1/market/orderbook/level1"
TOKEN_ENDPOINT = "/api/v1/bullet-public"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1500

# Intervals mapping: interval name -> seconds
INTERVALS: Dict[str, int] = {
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
    "1w": 604800
}

# Websocket supported intervals - KuCoin has limited websocket support for candles
WS_INTERVALS = ["1m"]
