"""
Exchange adapters for the Candles Feed package.
"""

from .ascend_ex.spot_adapter import AscendExSpotAdapter
from .binance.spot_adapter import BinanceSpotAdapter
from .bybit.spot_adapter import BybitSpotAdapter
from .coinbase_advanced_trade.spot_adapter import CoinbaseAdvancedTradeSpotAdapter
from .hyperliquid.spot_adapter import HyperliquidSpotAdapter
from .kraken.spot_adapter import KrakenSpotAdapter

from .binance.perpetual_adapter import BinancePerpetualAdapter
from .bybit.perpetual_adapter import BybitPerpetualAdapter
from .gate_io.perpetual_adapter import GateIoPerpetualAdapter
from .gate_io.spot_adapter import GateIoSpotAdapter
from .hyperliquid.perpetual_adapter import HyperliquidPerpetualAdapter
from .kucoin.perpetual_adapter import KucoinPerpetualAdapter
from .kucoin.spot_adapter import KucoinSpotAdapter
from .mexc.perpetual_adapter import MEXCPerpetualAdapter
from .mexc.spot_adapter import MEXCSpotAdapter
from .okx.perpetual_adapter import OKXPerpetualAdapter
from .okx.spot_adapter import OKXSpotAdapter

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
