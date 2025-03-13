"""
Exchange-specific plugins for the mock exchange server.

These plugins translate between the standardized mock server format
and the exchange-specific formats.
"""

from .ascend_ex import AscendExSpotPlugin
from .binance import BinanceSpotPlugin, BinancePerpetualPlugin
from .okx import OKXSpotPlugin, OKXPerpetualPlugin
from .bybit import BybitSpotPlugin, BybitPerpetualPlugin
from .coinbase_advanced_trade import CoinbaseAdvancedTradeSpotPlugin
from .kraken import KrakenSpotPlugin
from .mocked_plugin import MockedPlugin
from .gate_io import GateIoSpotPlugin, GateIoPerpetualPlugin
from .hyperliquid import HyperliquidSpotPlugin, HyperliquidPerpetualPlugin
from .kucoin import KucoinSpotPlugin, KucoinPerpetualPlugin
from .mexc import MEXCSpotPlugin, MEXCPerpetualPlugin


__all__ = [
    "BinanceSpotPlugin",
    "OKXSpotPlugin",
    "OKXPerpetualPlugin",
    "BybitSpotPlugin",
    "BybitPerpetualPlugin",
    "CoinbaseAdvancedTradeSpotPlugin",
    "KrakenSpotPlugin",
    "GateIoSpotPlugin",
    "HyperliquidSpotPlugin",
    "KucoinSpotPlugin",
    "MEXCSpotPlugin",
    "MockedPlugin",
]
