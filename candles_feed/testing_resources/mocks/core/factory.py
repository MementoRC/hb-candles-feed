"""
Server factory for creating mock exchange servers.
"""

import importlib
import logging
from typing import Dict, List, Optional, Tuple, Union

from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType


logger = logging.getLogger(__name__)


_PLUGIN_REGISTRY = {}


def register_plugin(exchange_type: ExchangeType, plugin):
    """
    Register an exchange plugin.
    
    Args:
        exchange_type: The exchange type
        plugin: The plugin instance
        
    Raises:
        ValueError: If a plugin is already registered for this exchange type
    """
    if exchange_type in _PLUGIN_REGISTRY:
        raise ValueError(f"Plugin already registered for exchange type {exchange_type.value}")
    
    _PLUGIN_REGISTRY[exchange_type] = plugin


def get_plugin(exchange_type: ExchangeType):
    """
    Get the plugin for an exchange type.
    
    Args:
        exchange_type: The exchange type
        
    Returns:
        The plugin instance, or None if not found
    """
    # Check if we already have a plugin registered
    if exchange_type in _PLUGIN_REGISTRY:
        return _PLUGIN_REGISTRY[exchange_type]
    
    # Try to import the plugin module
    try:
        # Convert exchange_type to a module path
        # e.g., binance_spot -> candles_feed.testing_resources.mocks.exchanges.binance_spot
        module_path = f"candles_feed.testing_resources.mocks.exchanges.{exchange_type.value}"
        module = importlib.import_module(module_path)
        
        # Get class name from exchange type
        # e.g., binance_spot -> BinanceSpotPlugin
        parts = exchange_type.value.split('_')
        class_name = ''.join(part.capitalize() for part in parts) + 'Plugin'
        
        # Get the plugin class
        plugin_class = getattr(module, class_name)
        
        # Create instance
        plugin = plugin_class(exchange_type)
        
        # Register
        _PLUGIN_REGISTRY[exchange_type] = plugin
        
        return plugin
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import plugin for {exchange_type.value}: {e}")
        return None


def create_mock_server(
    exchange_type: ExchangeType, 
    host: str = '127.0.0.1', 
    port: int = 8080,
    trading_pairs = None
):
    """
    Create a mock exchange server.
    
    Args:
        exchange_type: The type of exchange to mock
        host: The host to bind to
        port: The port to bind to
        trading_pairs: Optional list of trading pairs to initialize
                    Each tuple contains (symbol, interval, initial_price)
                    
    Returns:
        A configured MockExchangeServer instance, or None if the plugin
        for the specified exchange type cannot be found
    """
    # Import here to avoid circular imports
    from candles_feed.testing_resources.mocks.core.server import MockExchangeServer
    
    logger.info(f"Creating mock server for {exchange_type.value} at {host}:{port}")
    
    # Get the plugin for this exchange type
    plugin = get_plugin(exchange_type)
    if plugin is None:
        logger.error(f"No plugin found for exchange type {exchange_type.value}")
        return None
    
    # Create the server instance
    server = MockExchangeServer(plugin, host, port)
    
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
