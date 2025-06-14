"""
Common constants for HyperLiquid adapters.
"""

# API URLs - Common
REST_URL = "https://api.hyperliquid.xyz/info"
WSS_URL = "wss://api.hyperliquid.xyz/ws"

# API URLs - Spot
SPOT_REST_URL = REST_URL
SPOT_WSS_URL = WSS_URL
SPOT_CANDLES_ENDPOINT = ""  # HyperLiquid uses a single endpoint

# API URLs - Perpetual
PERPETUAL_REST_URL = REST_URL
PERPETUAL_WSS_URL = WSS_URL
PERPETUAL_CANDLES_ENDPOINT = ""  # HyperLiquid uses a single endpoint

# Alias for backward compatibility
PERP_WSS_URL = PERPETUAL_WSS_URL
PERP_REST_URL = PERPETUAL_REST_URL

# Health check constants
HEALTH_CHECK_PAYLOAD = {"type": "spotMeta"}

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 500

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

# Exchange-specific interval formats
INTERVAL_TO_EXCHANGE_FORMAT = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
    "12h": "720",
    "1d": "D",
    "1w": "W",
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())

# Channel names
CHANNEL_NAME = "candles"
