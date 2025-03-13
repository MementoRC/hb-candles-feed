"""
Candles Feed - A modular, plugin-based framework for fetching and managing candle data
from cryptocurrency exchanges.
"""

__version__ = "0.1.0"

# Import core components for easy access
from candles_feed.adapters.base_adapter import BaseAdapter

# Import exchange adapters
from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.adapters.bybit.spot_adapter import BybitSpotAdapter
from candles_feed.adapters.coinbase_advanced_trade.base_adapter import (
    CoinbaseAdvancedTradeBaseAdapter,
)
from candles_feed.adapters.kraken.spot_adapter import KrakenSpotAdapter
from candles_feed.adapters.kucoin.spot_adapter import KucoinSpotAdapter
from candles_feed.adapters.okx.spot_adapter import OKXSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.collection_strategies import (
    CollectionStrategyFactory,
    RESTPollingStrategy,
    WebSocketStrategy,
)

# Import integration helpers
from candles_feed.integration import create_candles_feed_with_hummingbot

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
    "CollectionStrategyFactory",
    # Base classes
    "BaseAdapter",
    # Exchange adapters
    "BinanceSpotAdapter",
    "BybitSpotAdapter",
    "CoinbaseAdvancedTradeBaseAdapter",
    "KrakenSpotAdapter",
    "KucoinSpotAdapter",
    "OKXSpotAdapter",
    # Integration helpers
    "create_candles_feed_with_hummingbot",
]
