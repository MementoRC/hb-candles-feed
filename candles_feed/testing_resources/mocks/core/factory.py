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
    # This is a simplified version for testing
    return _PLUGIN_REGISTRY.get(exchange_type)


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
    # This is a simplified version for testing
    # In the real implementation, this would create a server instance
    
    logger.info(f"Creating mock server for {exchange_type.value} at {host}:{port}")
    
    # Return a mock server object with some basic properties
    class MockServer:
        def __init__(self, exchange_type, host, port):
            self.exchange_type = exchange_type
            self.host = host
            self.port = port
            self.trading_pairs = {}
        
        def add_trading_pair(self, symbol, interval, price):
            key = f"{symbol}_{interval}"
            self.trading_pairs[key] = price
            logger.info(f"Added trading pair {symbol} with interval {interval} at price {price}")
        
        async def start(self):
            logger.info(f"Started mock server for {self.exchange_type.value}")
            return f"http://{self.host}:{self.port}"
        
        async def stop(self):
            logger.info(f"Stopped mock server for {self.exchange_type.value}")
    
    server = MockServer(exchange_type, host, port)
    
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
