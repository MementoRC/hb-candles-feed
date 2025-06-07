"""
Common constants for MEXC adapters.
"""

# API URLs - Spot
SPOT_REST_URL = "https://api.mexc.com"
SPOT_WSS_URL = "wss://wbs.mexc.com/ws"
SPOT_CANDLES_ENDPOINT = "/api/v3/klines"
SPOT_KLINE_TOPIC = "spot@public.kline."

# API URLs - Perpetual
PERPETUAL_REST_URL = "https://contract.mexc.com"
PERPETUAL_CANDLES_ENDPOINT = "/api/v1/contract/kline"
PERPETUAL_WSS_URL = "wss://contract.mexc.com/ws"
PERPETUAL_KLINE_TOPIC = "contract@kline."

# Legacy compatibility constants
PERP_REST_URL = PERPETUAL_REST_URL
PERP_CANDLES_ENDPOINT = PERPETUAL_CANDLES_ENDPOINT
PERP_WSS_URL = PERPETUAL_WSS_URL
PERP_KLINE_TOPIC = PERPETUAL_KLINE_TOPIC

# API endpoints
HEALTH_CHECK_ENDPOINT = "/api/v3/ping"

# WebSocket
SUB_ENDPOINT_NAME = "sub"

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1M": 2592000,
}

# MEXC interval formats mapping for spot
INTERVAL_TO_EXCHANGE_FORMAT = {
    "1m": "Min1",
    "5m": "Min5",
    "15m": "Min15",
    "30m": "Min30",
    "1h": "Min60",
    "4h": "Hour4",
    "1d": "Day1",
    "1M": "Month1",
}

# MEXC interval formats mapping for perpetual
INTERVAL_TO_PERPETUAL_FORMAT = {
    "1m": "Min1",
    "5m": "Min5",
    "15m": "Min15",
    "30m": "Min30",
    "1h": "Min60",
    "4h": "Hour4",
    "8h": "Hour8",
    "1d": "Day1",
    "1w": "Week1",
    "1M": "Month1",
}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())
