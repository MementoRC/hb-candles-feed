"""
Exchange adapters for the Candles Feed package.
"""

from candles_feed.adapters.ascend_ex.spot_adapter import AscendExSpotAdapter
from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.adapters.bybit.spot_adapter import BybitSpotAdapter
from candles_feed.adapters.coinbase_advanced_trade.spot_adapter import CoinbaseAdvancedTradeSpotAdapter
from candles_feed.adapters.hyperliquid.spot_adapter import HyperliquidSpotAdapter
from candles_feed.adapters.kraken.spot_adapter import KrakenSpotAdapter

from candles_feed.adapters.binance.perpetual_adapter import (
    BinancePerpetualAdapter,
)
from candles_feed.adapters.bybit.perpetual_adapter import BybitPerpetualAdapter
from candles_feed.adapters.gate_io.perpetual_adapter import GateIoPerpetualAdapter
from candles_feed.adapters.gate_io.spot_adapter import GateIoSpotAdapter
from candles_feed.adapters.hyperliquid.perpetual_adapter import HyperliquidPerpetualAdapter
from candles_feed.adapters.kucoin.perpetual_adapter import KucoinPerpetualAdapter
from candles_feed.adapters.kucoin.spot_adapter import KucoinSpotAdapter
from candles_feed.adapters.mexc.perpetual_adapter import MEXCPerpetualAdapter
from candles_feed.adapters.mexc.spot_adapter import MEXCSpotAdapter
from candles_feed.adapters.okx.perpetual_adapter import OKXPerpetualAdapter
from candles_feed.adapters.okx.spot_adapter import OKXSpotAdapter

__all__ = [
    # Spot adapters
    "AscendExSpotAdapter",
    "BinanceSpotAdapter",
    "BybitSpotAdapter",
    "CoinbaseAdvancedTradeSpotAdapter",
    "GateIoSpotAdapter",
    "HyperliquidSpotAdapter",
    "KrakenSpotAdapter",
    "KucoinSpotAdapter",
    "MEXCSpotAdapter",
    "OKXSpotAdapter",
    # Perpetual adapters
    "BinancePerpetualAdapter",
    "BybitPerpetualAdapter",
    "GateIoPerpetualAdapter",
    "HyperliquidPerpetualAdapter",
    "KucoinPerpetualAdapter",
    "MEXCPerpetualAdapter",
    "OKXPerpetualAdapter",
]
