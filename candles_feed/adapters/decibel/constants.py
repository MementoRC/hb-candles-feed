"""
Constants for the Decibel perpetual adapter.
"""

# Intervals mapping: interval name -> seconds (Decibel has no 1s/6h/3d/1w/1M candles)
INTERVALS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
}

# Decibel uses the same interval codes as our standard intervals
INTERVAL_TO_EXCHANGE_FORMAT: dict[str, str] = {k: k for k in INTERVALS}

# Websocket supported intervals
WS_INTERVALS: list[str] = list(INTERVALS.keys())

# The candlesticks endpoint has no limit parameter; this bounds the requested time window.
MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Domains (values mirror the upstream connector's domain names)
DEFAULT_DOMAIN = "decibel_perpetual"
NETNA_DOMAIN = "decibel_perpetual_netna"
TESTNET_DOMAIN = "decibel_perpetual_testnet"

# Mainnet
MAINNET_REST_URL = "https://api.mainnet.aptoslabs.com/decibel"
MAINNET_WSS_URL = "wss://api.mainnet.aptoslabs.com/decibel/ws"

# Netna (staging)
NETNA_REST_URL = "https://api.netna.staging.aptoslabs.com/decibel"
NETNA_WSS_URL = "wss://api.netna.staging.aptoslabs.com/decibel/ws"

# Testnet
TESTNET_REST_URL = "https://api.testnet.aptoslabs.com/decibel"
TESTNET_WSS_URL = "wss://api.testnet.aptoslabs.com/decibel/ws"

DOMAIN_TO_URLS: dict[str, tuple[str, str]] = {
    DEFAULT_DOMAIN: (MAINNET_REST_URL, MAINNET_WSS_URL),
    NETNA_DOMAIN: (NETNA_REST_URL, NETNA_WSS_URL),
    TESTNET_DOMAIN: (TESTNET_REST_URL, TESTNET_WSS_URL),
}

MARKETS_ENDPOINT = "/api/v1/markets"
CANDLES_ENDPOINT = "/api/v1/candlesticks"

WS_CANDLES_CHANNEL = "market_candlestick"
