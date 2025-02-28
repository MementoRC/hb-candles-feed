"""
Exchange adapters for the Candles Feed package.
"""

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.binance_spot.binance_spot_adapter import BinanceSpotAdapter
from candles_feed.adapters.bybit_spot.bybit_spot_adapter import BybitSpotAdapter
from candles_feed.adapters.coinbase_advanced_trade.coinbase_advanced_trade_adapter import CoinbaseAdvancedTradeAdapter
from candles_feed.adapters.kraken_spot.kraken_spot_adapter import KrakenSpotAdapter
from candles_feed.adapters.kucoin_spot.kucoin_spot_adapter import KuCoinSpotAdapter
from candles_feed.adapters.okx_spot.okx_spot_adapter import OKXSpotAdapter

__all__ = [
    "BaseAdapter",
    "BinanceSpotAdapter",
    "BybitSpotAdapter",
    "CoinbaseAdvancedTradeAdapter",
    "KrakenSpotAdapter",
    "KuCoinSpotAdapter",
    "OKXSpotAdapter"
]