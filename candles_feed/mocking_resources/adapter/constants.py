"""
Constants for simple mock adapter.
"""

# REST API URLs 
SPOT_REST_URL = "https://mock-exchange.test"
PERPETUAL_REST_URL = "https://mock-exchange.test"
REST_CANDLES_ENDPOINT = "/api/candles"

# WebSocket URLs
SPOT_WSS_URL = "wss://mock-exchange.test/ws"
PERPETUAL_WSS_URL = "wss://mock-exchange.test/ws"

# Mapping of interval names to seconds
INTERVALS = {
    "1s": 1,       # 1 second
    "1m": 60,      # 1 minute
    "3m": 180,     # 3 minutes
    "5m": 300,     # 5 minutes
    "15m": 900,    # 15 minutes
    "30m": 1800,   # 30 minutes
    "1h": 3600,    # 1 hour
    "2h": 7200,    # 2 hours
    "4h": 14400,   # 4 hours
    "6h": 21600,   # 6 hours
    "8h": 28800,   # 8 hours
    "12h": 43200,  # 12 hours
    "1d": 86400,   # 1 day
    "3d": 259200,  # 3 days
    "1w": 604800,  # 1 week
    "1M": 2592000, # 1 month (30 days)
}

# Default limit for candle requests
DEFAULT_CANDLES_LIMIT = 500