"""
Exchange-specific plugins for the mock exchange server.

These plugins translate between the standardized mock server format
and the exchange-specific formats.
"""

from .ascend_ex import AscendExSpotPlugin
from .binance import BinancePerpetualPlugin, BinanceSpotPlugin
from .bybit import BybitPerpetualPlugin, BybitSpotPlugin
from .coinbase_advanced_trade import CoinbaseAdvancedTradeSpotPlugin
from .gate_io import GateIoPerpetualPlugin, GateIoSpotPlugin
from .hyperliquid import HyperliquidPerpetualPlugin, HyperliquidSpotPlugin
from .kraken import KrakenSpotPlugin
from .kucoin import KucoinPerpetualPlugin, KucoinSpotPlugin
from .mexc import MEXCPerpetualPlugin, MEXCSpotPlugin
from .mocked_plugin import MockedPlugin
from .okx import OKXPerpetualPlugin, OKXSpotPlugin

__all__ = [
    "AscendExSpotPlugin",
    "BinancePerpetualPlugin",
    "BinanceSpotPlugin",
    "BybitPerpetualPlugin",
    "BybitSpotPlugin",
    "CoinbaseAdvancedTradeSpotPlugin",
    "GateIoPerpetualPlugin",
    "GateIoSpotPlugin",
    "HyperliquidPerpetualPlugin",
    "HyperliquidSpotPlugin",
    "KrakenSpotPlugin",
    "KucoinPerpetualPlugin",
    "KucoinSpotPlugin",
    "MEXCPerpetualPlugin",
    "MEXCSpotPlugin",
    "MockedPlugin",
    "OKXPerpetualPlugin",
    "OKXSpotPlugin",
]
