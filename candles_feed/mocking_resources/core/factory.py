"""
Server factory for creating mock exchange servers.
"""

import importlib
import logging
from typing import TypeVar, Optional, List, Tuple, Union

from candles_feed.mocking_resources.core.exchange_type import ExchangeType

logger = logging.getLogger(__name__)


_PLUGIN_REGISTRY = {}


def register_plugin(exchange_type: ExchangeType, plugin):
    """Register an exchange plugin.

    :param exchange_type: The exchange type
    :param plugin: The plugin instance
    :raises ValueError: If a plugin is already registered for this exchange type
    """
    if exchange_type in _PLUGIN_REGISTRY:
        raise ValueError(f"Plugin already registered for exchange type {exchange_type.value}")

    _PLUGIN_REGISTRY[exchange_type] = plugin


def get_plugin(exchange_type: ExchangeType):
    """Get the plugin for an exchange type.

    :param exchange_type: ExchangeType:
    :returns: The plugin instance, or None if not found
    """
    # Check if we already have a plugin registered
    if exchange_type in _PLUGIN_REGISTRY:
        return _PLUGIN_REGISTRY[exchange_type]

    # Try to import the plugin module
    try:
        # Convert exchange_type to a module path
        # e.g., binance_spot -> candles_feed.mocking_resources.exchanges.binance.spot_plugin
        module_path = f"candles_feed.mocking_resources.exchanges.{exchange_type.value.replace('_', '.')}_plugin"
        module = importlib.import_module(module_path)

        # Get class name from exchange type
        # e.g., binance_spot -> BinanceSpotPlugin
        parts = exchange_type.value.split("_")
        class_name = "".join(part.capitalize() for part in parts) + "Plugin"

        # Get the plugin class
        plugin_class = getattr(module, class_name)

        # Create instance
        plugin = plugin_class()

        # Register
        _PLUGIN_REGISTRY[exchange_type] = plugin

        return plugin
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import plugin for {exchange_type.value}: {e}")
        return None


MockCandlesFeedServerT = TypeVar("MockCandlesFeedServerT", bound="MockedExchangeServer")

def create_mock_server(
    exchange_type: ExchangeType,
        host: str = "127.0.0.1",
        port: int = 8080,
        trading_pairs=None
) -> MockCandlesFeedServerT | None:
    """Create a mock exchange server.

    :param exchange_type: The type of exchange to mock
    :param host: The host to bind to (Default value = "127.0.0.1")
    :param port: The port to bind to (Default value = 8080)
    :param trading_pairs: Optional list of trading pairs to initialize
                    Each tuple contains (symbol, interval, initial_price) (Default value = None)
    :returns: A configured MockedExchangeServer instance, or None if the plugin
        for the specified exchange type cannot be found
    """
    # Import here to avoid circular imports
    from candles_feed.mocking_resources.core.server import MockedExchangeServer

    logger.info(f"Creating mock server for {exchange_type.value} at {host}:{port}")

    # Get the plugin for this exchange type
    plugin = get_plugin(exchange_type)
    if plugin is None:
        logger.error(f"No plugin found for exchange type {exchange_type.value}")
        return None

    # Create the server instance
    server = MockedExchangeServer(plugin, host, port)

    # Add trading pairs
    if trading_pairs:
        for symbol, interval, price in trading_pairs:
            server.add_trading_pair(symbol, interval, price)
    else:
        # Add some default trading pairs
        server.add_trading_pair("BTCUSDT", "1m", 50000.0)
        server.add_trading_pair("ETHUSDT", "1m", 3000.0)
        server.add_trading_pair("SOLUSDT", "1m", 100.0)

    return server


def create_mock_server_for_exchange(
    exchange_type: ExchangeType,
    host: str = "127.0.0.1",
    port: int = 8080,
    trading_pairs: Optional[List[Tuple[str, str, float]]] = None
) -> Optional[MockCandlesFeedServerT]:
    """Create a mock server for a specific exchange.
    
    This is a convenience wrapper around create_mock_server that handles 
    exchange-specific configuration.
    
    :param exchange_type: The type of exchange to mock
    :param host: The host to bind to (Default value = "127.0.0.1")
    :param port: The port to bind to (Default value = 8080)
    :param trading_pairs: Optional list of trading pairs to initialize
                Each tuple contains (symbol, interval, initial_price) (Default value = None)
    :returns: A configured MockedExchangeServer instance
    """
    # Use the plugins we already imported at the module level
    
    server = create_mock_server(exchange_type, host, port, trading_pairs)
    
    if server is None:
        # Fallback to manual plugin creation
        from candles_feed.mocking_resources.core.server import MockedExchangeServer
        
        if exchange_type == ExchangeType.BINANCE_SPOT:
            from candles_feed.mocking_resources.exchanges.binance.spot_plugin import BinanceSpotPlugin
            plugin = BinanceSpotPlugin()
        elif exchange_type == ExchangeType.BINANCE_PERPETUAL:
            from candles_feed.mocking_resources.exchanges.binance.perpetual_plugin import BinancePerpetualPlugin
            plugin = BinancePerpetualPlugin()
        elif exchange_type == ExchangeType.OKX_SPOT:
            from candles_feed.mocking_resources.exchanges.okx.spot_plugin import OKXSpotPlugin
            plugin = OKXSpotPlugin()
        elif exchange_type == ExchangeType.OKX_PERPETUAL:
            from candles_feed.mocking_resources.exchanges.okx.perpetual_plugin import OKXPerpetualPlugin
            plugin = OKXPerpetualPlugin()
        elif exchange_type == ExchangeType.BYBIT_SPOT:
            from candles_feed.mocking_resources.exchanges.bybit.spot_plugin import BybitSpotPlugin
            plugin = BybitSpotPlugin()
        elif exchange_type == ExchangeType.BYBIT_PERPETUAL:
            from candles_feed.mocking_resources.exchanges.bybit.perpetual_plugin import BybitPerpetualPlugin
            plugin = BybitPerpetualPlugin()
        elif exchange_type == ExchangeType.COINBASE_ADVANCED_TRADE:
            from candles_feed.mocking_resources.exchanges.coinbase_advanced_trade.spot_plugin import CoinbaseAdvancedTradeSpotPlugin
            plugin = CoinbaseAdvancedTradeSpotPlugin()
        elif exchange_type == ExchangeType.KRAKEN_SPOT:
            from candles_feed.mocking_resources.exchanges.kraken.spot_plugin import KrakenSpotPlugin
            plugin = KrakenSpotPlugin()
        elif exchange_type == ExchangeType.KUCOIN_SPOT:
            from candles_feed.mocking_resources.exchanges.kucoin.spot_plugin import KucoinSpotPlugin
            plugin = KucoinSpotPlugin()
        elif exchange_type == ExchangeType.KUCOIN_PERPETUAL:
            from candles_feed.mocking_resources.exchanges.kucoin.perpetual_plugin import KucoinPerpetualPlugin
            plugin = KucoinPerpetualPlugin()
        elif exchange_type == ExchangeType.GATE_IO_SPOT:
            from candles_feed.mocking_resources.exchanges.gate_io.spot_plugin import GateIoSpotPlugin
            plugin = GateIoSpotPlugin()
        elif exchange_type == ExchangeType.GATE_IO_PERPETUAL:
            from candles_feed.mocking_resources.exchanges.gate_io.perpetual_plugin import GateIoPerpetualPlugin
            plugin = GateIoPerpetualPlugin()
        elif exchange_type == ExchangeType.MEXC_SPOT:
            from candles_feed.mocking_resources.exchanges.mexc.spot_plugin import MEXCSpotPlugin
            plugin = MEXCSpotPlugin()
        elif exchange_type == ExchangeType.MEXC_PERPETUAL:
            from candles_feed.mocking_resources.exchanges.mexc.perpetual_plugin import MEXCPerpetualPlugin
            plugin = MEXCPerpetualPlugin()
        elif exchange_type == ExchangeType.HYPERLIQUID_SPOT:
            from candles_feed.mocking_resources.exchanges.hyperliquid.spot_plugin import HyperliquidSpotPlugin
            plugin = HyperliquidSpotPlugin()
        elif exchange_type == ExchangeType.HYPERLIQUID_PERPETUAL:
            from candles_feed.mocking_resources.exchanges.hyperliquid.perpetual_plugin import HyperliquidPerpetualPlugin
            plugin = HyperliquidPerpetualPlugin()
        elif exchange_type == ExchangeType.ASCEND_EX_SPOT:
            from candles_feed.mocking_resources.exchanges.ascend_ex.spot_plugin import AscendExSpotPlugin
            plugin = AscendExSpotPlugin()
        else:
            logger.error(f"No plugin implementation found for {exchange_type.value}")
            return None
        
        server = MockedExchangeServer(plugin, host, port)
        
        # Add trading pairs
        if trading_pairs:
            for symbol, interval, price in trading_pairs:
                server.add_trading_pair(symbol, interval, price)
        else:
            # Add some default trading pairs
            server.add_trading_pair("BTC-USDT", "1m", 50000.0)
            server.add_trading_pair("ETH-USDT", "1m", 3000.0)
            server.add_trading_pair("SOL-USDT", "1m", 100.0)
    
    return server
