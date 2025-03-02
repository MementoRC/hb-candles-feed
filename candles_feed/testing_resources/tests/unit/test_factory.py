"""
Unit tests for the server factory.
"""

import unittest
from unittest.mock import patch, MagicMock

from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType
from candles_feed.testing_resources.mocks.core.factory import (
    register_plugin, get_plugin, create_mock_server, _PLUGIN_REGISTRY
)


class TestFactory(unittest.TestCase):
    """Tests for the mock server factory functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear the plugin registry before each test
        _PLUGIN_REGISTRY.clear()
    
    def test_register_plugin(self):
        """Test registering a plugin."""
        # Arrange
        exchange_type = ExchangeType.BINANCE_SPOT
        mock_plugin = MagicMock()
        
        # Act
        register_plugin(exchange_type, mock_plugin)
        
        # Assert
        self.assertIn(exchange_type, _PLUGIN_REGISTRY)
        self.assertEqual(_PLUGIN_REGISTRY[exchange_type], mock_plugin)
    
    def test_register_plugin_duplicate(self):
        """Test that registering a duplicate plugin raises an error."""
        # Arrange
        exchange_type = ExchangeType.BINANCE_SPOT
        mock_plugin = MagicMock()
        register_plugin(exchange_type, mock_plugin)
        
        # Act/Assert
        with self.assertRaises(ValueError):
            register_plugin(exchange_type, mock_plugin)
    
    def test_get_plugin_registered(self):
        """Test getting a registered plugin."""
        # Arrange
        exchange_type = ExchangeType.BINANCE_SPOT
        mock_plugin = MagicMock()
        register_plugin(exchange_type, mock_plugin)
        
        # Act
        plugin = get_plugin(exchange_type)
        
        # Assert
        self.assertEqual(plugin, mock_plugin)
    
    @patch('importlib.import_module')
    def test_get_plugin_auto_import(self, mock_import):
        """Test that get_plugin auto-imports plugins."""
        # Arrange
        exchange_type = ExchangeType.BINANCE_SPOT
        mock_plugin_class = MagicMock()
        mock_plugin_instance = MagicMock()
        mock_plugin_class.return_value = mock_plugin_instance
        
        # Mock the module import and attribute access
        mock_module = MagicMock()
        mock_module.BinanceSpotPlugin = mock_plugin_class
        mock_import.return_value = mock_module
        
        # Act
        plugin = get_plugin(exchange_type)
        
        # Assert
        mock_import.assert_called_once_with(
            'candles_feed.testing_resources.mocks.exchanges.binance_spot'
        )
        mock_plugin_class.assert_called_once_with(exchange_type)
        self.assertEqual(plugin, mock_plugin_instance)
        self.assertIn(exchange_type, _PLUGIN_REGISTRY)
    
    @patch('importlib.import_module')
    def test_get_plugin_import_error(self, mock_import):
        """Test handling of import errors."""
        # Arrange
        exchange_type = ExchangeType.BINANCE_SPOT
        mock_import.side_effect = ImportError("Module not found")
        
        # Act
        plugin = get_plugin(exchange_type)
        
        # Assert
        self.assertIsNone(plugin)
        self.assertNotIn(exchange_type, _PLUGIN_REGISTRY)
    
    @patch('candles_feed.testing_resources.mocks.core.factory.get_plugin')
    @patch('candles_feed.testing_resources.mocks.core.server.MockExchangeServer')
    def test_create_mock_server(self, mock_server_class, mock_get_plugin):
        """Test creating a mock server."""
        # Arrange
        exchange_type = ExchangeType.BINANCE_SPOT
        mock_plugin = MagicMock()
        mock_get_plugin.return_value = mock_plugin
        
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        # Act
        server = create_mock_server(
            exchange_type=exchange_type,
            host='test_host',
            port=1234,
            trading_pairs=[('BTCUSDT', '1m', 50000.0)]
        )
        
        # Assert
        mock_get_plugin.assert_called_once_with(exchange_type)
        mock_server_class.assert_called_once_with(mock_plugin, 'test_host', 1234)
        mock_server.add_trading_pair.assert_called_once_with('BTCUSDT', '1m', 50000.0)
        self.assertEqual(server, mock_server)
    
    @patch('candles_feed.testing_resources.mocks.core.factory.get_plugin')
    def test_create_mock_server_no_plugin(self, mock_get_plugin):
        """Test handling when no plugin is found."""
        # Arrange
        exchange_type = ExchangeType.BINANCE_SPOT
        mock_get_plugin.return_value = None
        
        # Act
        server = create_mock_server(exchange_type=exchange_type)
        
        # Assert
        mock_get_plugin.assert_called_once_with(exchange_type)
        self.assertIsNone(server)
    
    @patch('candles_feed.testing_resources.mocks.core.factory.get_plugin')
    @patch('candles_feed.testing_resources.mocks.core.server.MockExchangeServer')
    def test_create_mock_server_default_trading_pairs(self, mock_server_class, mock_get_plugin):
        """Test creating a mock server with default trading pairs."""
        # Arrange
        exchange_type = ExchangeType.BINANCE_SPOT
        mock_plugin = MagicMock()
        mock_get_plugin.return_value = mock_plugin
        
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        # Act
        server = create_mock_server(exchange_type=exchange_type)
        
        # Assert
        mock_get_plugin.assert_called_once_with(exchange_type)
        mock_server_class.assert_called_once_with(mock_plugin, '127.0.0.1', 8080)
        
        # Check that default trading pairs are added
        self.assertEqual(mock_server.add_trading_pair.call_count, 3)
        mock_server.add_trading_pair.assert_any_call('BTCUSDT', '1m', 50000.0)
        mock_server.add_trading_pair.assert_any_call('ETHUSDT', '1m', 3000.0)
        mock_server.add_trading_pair.assert_any_call('SOLUSDT', '1m', 100.0)
        
        self.assertEqual(server, mock_server)


if __name__ == '__main__':
    unittest.main()