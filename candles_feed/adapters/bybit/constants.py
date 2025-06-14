"""
Common constants for Bybit adapters.
"""

# API URLs - Common
SPOT_REST_URL = "https://api.bybit.com"
SPOT_CANDLES_ENDPOINT = "/v5/market/kline"
SERVER_TIME_ENDPOINT = "/v5/market/time"
HEALTH_CHECK_ENDPOINT = SERVER_TIME_ENDPOINT

# API URLs - Spot
SPOT_WSS_URL = "wss://stream.bybit.com/v5/public/spot"

# API URLs - Perpetual
PERPETUAL_REST_URL = "https://api.bybit.com"
PERPETUAL_CANDLES_ENDPOINT = "/v5/market/kline"
PERPETUAL_WSS_URL = "wss://stream.bybit.com/v5/public/linear"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

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
    "12h": 43200,
    "1d": 86400,
    "1w": 604800,
    "1M": 2592000,
}

# Exchange-specific interval formats
INTERVAL_TO_EXCHANGE_FORMAT = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "2h": "120",
    "4h": "240",
    "6h": "360",
    "12h": "720",
    "1d": "D",
    "1w": "W",
    "1M": "M",
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())
