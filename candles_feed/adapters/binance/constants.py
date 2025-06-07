"""
Common constants for Binance adapters.
"""

# Intervals mapping: interval name -> seconds
INTERVALS: dict[str, int] = {
    "1s": 1,
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
    "3d": 259200,
    "1w": 604800,
    "1M": 2592000,
}

# OKX interval formats - Binance uses the same format as our standard intervals
INTERVAL_TO_EXCHANGE_FORMAT = {k: k for k in INTERVALS}

# Websocket supported intervals
WS_INTERVALS = list(INTERVALS.keys())

# API rate limits
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# API URLs and endpoints
# Spot Production
SPOT_REST_URL = "https://api.binance.com"
SPOT_CANDLES_ENDPOINT = "/api/v3/klines"
SPOT_WSS_URL = "wss://stream.binance.com:9443/ws"
SPOT_HEALTH_CHECK_ENDPOINT = "/api/v3/ping"

# Spot Testnet
SPOT_TESTNET_REST_URL = "https://testnet.binance.vision"
SPOT_TESTNET_WSS_URL = "wss://testnet.binance.vision/ws"

# Perpetual Production
PERPETUAL_REST_URL = "https://fapi.binance.com"
PERPETUAL_CANDLES_ENDPOINT = "/fapi/v1/klines"
PERPETUAL_WSS_URL = "wss://fstream.binance.com/ws"
PERPETUAL_HEALTH_CHECK_ENDPOINT = "/fapi/v1/ping"

# Perpetual Testnet
PERPETUAL_TESTNET_REST_URL = "https://testnet.binancefuture.com"
PERPETUAL_TESTNET_WSS_URL = "wss://stream.binancefuture.com/ws"
