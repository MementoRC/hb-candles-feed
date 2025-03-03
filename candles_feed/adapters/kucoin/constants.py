"""
Common constants for KuCoin adapters.
"""

from typing import Dict

# API URLs - Common
REST_BASE_URL = "https://api.kucoin.com"
WSS_BASE_URL = "wss://ws-api.kucoin.com"

# API URLs - Spot
SPOT_REST_URL = REST_BASE_URL
SPOT_CANDLES_ENDPOINT = "/api/v1/market/candles"
SPOT_WSS_URL = WSS_BASE_URL

# API URLs - Perpetual
PERP_REST_URL = "https://api-futures.kucoin.com"
PERP_CANDLES_ENDPOINT = "/api/v1/kline/query"
PERP_WSS_URL = "wss://ws-api-futures.kucoin.com"

# API endpoints
TICKER_ENDPOINT = "/api/v1/market/orderbook/level1"
TOKEN_ENDPOINT = "/api/v1/bullet-public"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1500

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
    "1w": 604800,
}

# KuCoin interval formats mapping - perpetual uses different format for some intervals
INTERVAL_TO_KUCOIN_PERP_FORMAT = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1hour",
    "4h": "4hour",
    "8h": "8hour",
    "12h": "12hour",
    "1d": "1day",
    "1w": "1week",
}

# Websocket supported intervals - KuCoin has limited websocket support for candles
WS_INTERVALS = ["1m"]
