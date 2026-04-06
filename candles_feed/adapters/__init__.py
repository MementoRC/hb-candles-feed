"""
Exchange adapters for the Candles Feed package.
"""

from .aevo.perpetual_adapter import AevoPerpetualAdapter
from .ascend_ex.spot_adapter import AscendExSpotAdapter
from .binance.perpetual_adapter import BinancePerpetualAdapter
from .binance.spot_adapter import BinanceSpotAdapter
from .bitget.perpetual_adapter import BitgetPerpetualAdapter
from .bitget.spot_adapter import BitgetSpotAdapter
from .bitmart.perpetual_adapter import BitmartPerpetualAdapter
from .btc_markets.spot_adapter import BTCMarketsSpotAdapter
from .bybit.perpetual_adapter import BybitPerpetualAdapter
from .bybit.spot_adapter import BybitSpotAdapter
from .coinbase_advanced_trade.spot_adapter import CoinbaseAdvancedTradeSpotAdapter
from .dexalot.spot_adapter import DexalotSpotAdapter
from .gate_io.perpetual_adapter import GateIoPerpetualAdapter
from .gate_io.spot_adapter import GateIoSpotAdapter
from .hyperliquid.perpetual_adapter import HyperliquidPerpetualAdapter
from .hyperliquid.spot_adapter import HyperliquidSpotAdapter
from .kraken.spot_adapter import KrakenSpotAdapter
from .kucoin.perpetual_adapter import KucoinPerpetualAdapter
from .kucoin.spot_adapter import KucoinSpotAdapter
from .mexc.perpetual_adapter import MEXCPerpetualAdapter
from .mexc.spot_adapter import MEXCSpotAdapter
from .okx.perpetual_adapter import OKXPerpetualAdapter
from .okx.spot_adapter import OKXSpotAdapter
from .pacifica.perpetual_adapter import PacificaPerpetualAdapter

__all__ = [
    # Spot adapters
    "AscendExSpotAdapter",
    "BinanceSpotAdapter",
    "BitgetSpotAdapter",
    "BTCMarketsSpotAdapter",
    "BybitSpotAdapter",
    "CoinbaseAdvancedTradeSpotAdapter",
    "DexalotSpotAdapter",
    "GateIoSpotAdapter",
    "HyperliquidSpotAdapter",
    "KrakenSpotAdapter",
    "KucoinSpotAdapter",
    "MEXCSpotAdapter",
    "OKXSpotAdapter",
    # Perpetual adapters
    "AevoPerpetualAdapter",
    "BinancePerpetualAdapter",
    "BitgetPerpetualAdapter",
    "BitmartPerpetualAdapter",
    "BybitPerpetualAdapter",
    "GateIoPerpetualAdapter",
    "HyperliquidPerpetualAdapter",
    "KucoinPerpetualAdapter",
    "MEXCPerpetualAdapter",
    "OKXPerpetualAdapter",
    "PacificaPerpetualAdapter",
]
