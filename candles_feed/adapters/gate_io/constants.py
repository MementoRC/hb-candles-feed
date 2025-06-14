"""
Common constants for Gate.io adapters.
"""

# API URLs - Common
REST_URL = "https://api.gateio.ws/api/v4"
WSS_URL = "wss://api.gateio.ws/ws/v4/"

# API URLs - Spot
SPOT_REST_URL = REST_URL
SPOT_WSS_URL = WSS_URL
SPOT_CANDLES_ENDPOINT = "/spot/candlesticks"
SPOT_CHANNEL_NAME = "spot.candlesticks"

# API URLs - Perpetual
PERPETUAL_REST_URL = REST_URL
PERPETUAL_WSS_URL = WSS_URL
PERPETUAL_CANDLES_ENDPOINT = "/futures/usdt/candlesticks"
PERPETUAL_CHANNEL_NAME = "futures.candlesticks"

# Legacy/compatibility constants
PERP_CANDLES_ENDPOINT = PERPETUAL_CANDLES_ENDPOINT
PERP_CHANNEL_NAME = PERPETUAL_CHANNEL_NAME
PERP_WSS_URL = PERPETUAL_WSS_URL

# Health check endpoint
HEALTH_CHECK_ENDPOINT = "/spot/currencies/BTC"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {
    "10s": 10,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "8h": 28800,
    "1d": 86400,
    "7d": 604800,
}

# Exchange-specific interval formats
INTERVAL_TO_EXCHANGE_FORMAT = {
    "10s": "10s",
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "8h": "8h",
    "1d": "1d",
    "7d": "7d",
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())
