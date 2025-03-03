"""
Exchange adapters for the Candles Feed package.
"""

# Base adapters
# Spot adapters
from candles_feed.adapters.ascend_ex_spot.ascend_ex_spot_adapter import AscendExSpotAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.binance.binance_base_adapter import BinanceBaseAdapter

# Perpetual adapters
from candles_feed.adapters.binance_perpetual.binance_perpetual_adapter import (
    BinancePerpetualAdapter,
)
from candles_feed.adapters.binance_spot.binance_spot_adapter import BinanceSpotAdapter
from candles_feed.adapters.bybit.bybit_base_adapter import BybitBaseAdapter
from candles_feed.adapters.bybit_perpetual.bybit_perpetual_adapter import BybitPerpetualAdapter
from candles_feed.adapters.bybit_spot.bybit_spot_adapter import BybitSpotAdapter
from candles_feed.adapters.coinbase_advanced_trade.coinbase_advanced_trade_adapter import (
    CoinbaseAdvancedTradeAdapter,
)
from candles_feed.adapters.gate_io.gate_io_base_adapter import GateIoBaseAdapter
from candles_feed.adapters.gate_io_perpetual.gate_io_perpetual_adapter import GateIoPerpetualAdapter
from candles_feed.adapters.gate_io_spot.gate_io_spot_adapter import GateIoSpotAdapter
from candles_feed.adapters.hyperliquid.hyperliquid_base_adapter import HyperliquidBaseAdapter
from candles_feed.adapters.hyperliquid_perpetual.hyperliquid_perpetual_adapter import (
    HyperliquidPerpetualAdapter,
)
from candles_feed.adapters.hyperliquid_spot.hyperliquid_spot_adapter import HyperliquidSpotAdapter
from candles_feed.adapters.kraken_spot.kraken_spot_adapter import KrakenSpotAdapter
from candles_feed.adapters.kucoin.kucoin_base_adapter import KuCoinBaseAdapter
from candles_feed.adapters.kucoin_perpetual.kucoin_perpetual_adapter import KuCoinPerpetualAdapter
from candles_feed.adapters.kucoin_spot.kucoin_spot_adapter import KuCoinSpotAdapter
from candles_feed.adapters.mexc.mexc_base_adapter import MEXCBaseAdapter
from candles_feed.adapters.mexc_perpetual.mexc_perpetual_adapter import MEXCPerpetualAdapter
from candles_feed.adapters.mexc_spot.mexc_spot_adapter import MEXCSpotAdapter
from candles_feed.adapters.okx.okx_base_adapter import OKXBaseAdapter
from candles_feed.adapters.okx_perpetual.okx_perpetual_adapter import OKXPerpetualAdapter
from candles_feed.adapters.okx_spot.okx_spot_adapter import OKXSpotAdapter

__all__ = [
    # Base adapters
    "BaseAdapter",
    "BinanceBaseAdapter",
    "BybitBaseAdapter",
    "GateIoBaseAdapter",
    "HyperliquidBaseAdapter",
    "KuCoinBaseAdapter",
    "MEXCBaseAdapter",
    "OKXBaseAdapter",
    # Spot adapters
    "AscendExSpotAdapter",
    "BinanceSpotAdapter",
    "BybitSpotAdapter",
    "CoinbaseAdvancedTradeAdapter",
    "GateIoSpotAdapter",
    "HyperliquidSpotAdapter",
    "KrakenSpotAdapter",
    "KuCoinSpotAdapter",
    "MEXCSpotAdapter",
    "OKXSpotAdapter",
    # Perpetual adapters
    "BinancePerpetualAdapter",
    "BybitPerpetualAdapter",
    "GateIoPerpetualAdapter",
    "HyperliquidPerpetualAdapter",
    "KuCoinPerpetualAdapter",
    "MEXCPerpetualAdapter",
    "OKXPerpetualAdapter",
]
