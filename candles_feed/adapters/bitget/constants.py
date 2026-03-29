"""
Common constants for Bitget adapters.
"""

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "6h": 21600,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
}

# Spot interval format - Bitget spot uses different naming
SPOT_INTERVAL_TO_EXCHANGE: dict[str, str] = {
    "1m": "1min",
    "3m": "3min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "6h": "6h",
    "12h": "12h",
    "1d": "1day",
    "3d": "3day",
    "1w": "1week",
}

# Perpetual interval format - Bitget perpetual uses uppercase suffixes
PERPETUAL_INTERVAL_TO_EXCHANGE: dict[str, str] = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "4h": "4H",
    "6h": "6H",
    "12h": "12H",
    "1d": "1D",
    "3d": "3D",
    "1w": "1W",
}

# WebSocket interval format - same as perpetual
WS_INTERVAL_TO_EXCHANGE: dict[str, str] = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "4h": "4H",
    "6h": "6H",
    "12h": "12H",
    "1d": "1D",
    "3d": "3D",
    "1w": "1W",
}

# WebSocket supported intervals
WS_INTERVALS: list[str] = list(WS_INTERVAL_TO_EXCHANGE.keys())

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# API URLs and endpoints
# Spot
SPOT_REST_URL = "https://api.bitget.com"
SPOT_CANDLES_ENDPOINT = "/api/v2/spot/market/candles"

# Perpetual
PERPETUAL_REST_URL = "https://api.bitget.com"
PERPETUAL_CANDLES_ENDPOINT = "/api/v2/mix/market/candles"

# WebSocket
WSS_URL = "wss://ws.bitget.com/v2/ws/public"
