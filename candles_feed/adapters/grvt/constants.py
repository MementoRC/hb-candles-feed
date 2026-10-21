"""
Constants for the GRVT perpetual adapter.

URL, path and channel values are copied from the hummingbot grvt_perpetual
connector constants (they are not imported).
"""

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
    "3d": 259200,
    "1w": 604800,
}

# Interval name -> GRVT candle interval code
INTERVAL_TO_EXCHANGE_FORMAT: dict[str, str] = {
    "1m": "CI_1_M",
    "3m": "CI_3_M",
    "5m": "CI_5_M",
    "15m": "CI_15_M",
    "30m": "CI_30_M",
    "1h": "CI_1_H",
    "2h": "CI_2_H",
    "4h": "CI_4_H",
    "6h": "CI_6_H",
    "8h": "CI_8_H",
    "12h": "CI_12_H",
    "1d": "CI_1_D",
    "3d": "CI_3_D",
    "1w": "CI_1_W",
}

# Websocket supported intervals
WS_INTERVALS: list[str] = list(INTERVALS.keys())

MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST = 1000

# Market-data hosts (public endpoints)
MAINNET_REST_URL = "https://market-data.grvt.io"
MAINNET_WSS_URL = "wss://market-data.grvt.io/ws/full"
TESTNET_REST_URL = "https://market-data.testnet.grvt.io"
TESTNET_WSS_URL = "wss://market-data.testnet.grvt.io/ws/full"

# Paths (relative, joined with "/")
KLINE_PATH_URL = "full/v1/kline"

# Websocket candle stream name
PUBLIC_WS_CHANNEL_CANDLE = "v1.candle"

# Candle price type requested from the API
CANDLE_TYPE = "TRADE"

NANOSECONDS_PER_SECOND = 1_000_000_000
