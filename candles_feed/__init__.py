"""
Candles Feed - A modular, plugin-based framework for fetching and managing candle data
from cryptocurrency exchanges.
"""

__version__ = "0.1.0"

# Import core components for easy access
from candles_feed.adapters.base_adapter import BaseAdapter

# Import exchange adapters
from candles_feed.adapters.binance_spot.binance_spot_adapter import BinanceSpotAdapter
from candles_feed.adapters.bybit_spot.bybit_spot_adapter import BybitSpotAdapter
from candles_feed.adapters.coinbase_advanced_trade.coinbase_advanced_trade_adapter import (
    CoinbaseAdvancedTradeAdapter,
)
from candles_feed.adapters.kraken_spot.kraken_spot_adapter import KrakenSpotAdapter
from candles_feed.adapters.kucoin_spot.kucoin_spot_adapter import KuCoinSpotAdapter
from candles_feed.adapters.okx_spot.okx_spot_adapter import OKXSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.network_strategies import (
    NetworkStrategyFactory,
    RESTPollingStrategy,
    WebSocketStrategy,
)

# Auto-discover exchange adapters if any are installed
try:
    ExchangeRegistry.discover_adapters()
except Exception as e:
    import logging

    logging.getLogger(__name__).warning(f"Error discovering exchange adapters: {e}")

__all__ = [
    # Core components
    "CandleData",
    "CandlesFeed",
    "ExchangeRegistry",
    "DataProcessor",
    "NetworkClient",
    "WebSocketStrategy",
    "RESTPollingStrategy",
    "NetworkStrategyFactory",
    # Base classes
    "BaseAdapter",
    # Exchange adapters
    "BinanceSpotAdapter",
    "BybitSpotAdapter",
    "CoinbaseAdvancedTradeAdapter",
    "KrakenSpotAdapter",
    "KuCoinSpotAdapter",
    "OKXSpotAdapter",
]
