"""
Exchange-specific plugins for the mock exchange server.

These plugins translate between the standardized mock server format
and the exchange-specific formats.
"""

from .aevo import AevoPerpetualPlugin
from .ascend_ex import AscendExSpotPlugin
from .binance import BinancePerpetualPlugin, BinanceSpotPlugin
from .bitget import BitgetPerpetualPlugin, BitgetSpotPlugin
from .bitmart import BitmartPerpetualPlugin
from .btc_markets import BTCMarketsSpotPlugin
from .bybit import BybitPerpetualPlugin, BybitSpotPlugin
from .coinbase_advanced_trade import CoinbaseAdvancedTradeSpotPlugin
from .dexalot import DexalotSpotPlugin
from .gate_io import GateIoPerpetualPlugin, GateIoSpotPlugin
from .hyperliquid import HyperliquidPerpetualPlugin, HyperliquidSpotPlugin
from .kraken import KrakenSpotPlugin
from .kucoin import KucoinPerpetualPlugin, KucoinSpotPlugin
from .mexc import MEXCPerpetualPlugin, MEXCSpotPlugin
from .mocked_plugin import MockedPlugin
from .okx import OKXPerpetualPlugin, OKXSpotPlugin
from .pacifica import PacificaPerpetualPlugin

__all__ = [
    "AevoPerpetualPlugin",
    "AscendExSpotPlugin",
    "BTCMarketsSpotPlugin",
    "BinancePerpetualPlugin",
    "BinanceSpotPlugin",
    "BitgetPerpetualPlugin",
    "BitgetSpotPlugin",
    "BitmartPerpetualPlugin",
    "BybitPerpetualPlugin",
    "BybitSpotPlugin",
    "CoinbaseAdvancedTradeSpotPlugin",
    "DexalotSpotPlugin",
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
    "PacificaPerpetualPlugin",
]
