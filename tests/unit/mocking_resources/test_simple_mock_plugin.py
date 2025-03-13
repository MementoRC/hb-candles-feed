"""
Unit tests for MockedPlugin.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin import MockedPlugin


class TestMockedPlugin:
    """Test suite for MockedPlugin."""

    def setup_method(self):
        """Set up test fixtures."""
        self.plugin = MockedPlugin(ExchangeType.MOCK)
        
        # Add some trading pairs
        self.plugin.add_trading_pair("BTC-USDT", "1m", 50000.0)
        self.plugin.add_trading_pair("ETH-USDT", "1m", 3000.0)
        self.plugin.add_trading_pair("SOL-USDT", "1m", 100.0)

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.MOCK
        
    def test_get_base_price(self):
        """Test retrieving base prices for trading pairs."""
        assert self.plugin.get_base_price("BTC-USDT") == 50000.0
        assert self.plugin.get_base_price("ETH-USDT") == 3000.0
        assert self.plugin.get_base_price("SOL-USDT") == 100.0
        
        # Default price for unknown pairs
        assert self.plugin.get_base_price("UNKNOWN-PAIR") == 100.0
        
    def test_get_interval_seconds(self):
        """Test conversion of interval strings to seconds."""
        assert self.plugin.get_interval_seconds("1s") == 1
        assert self.plugin.get_interval_seconds("1m") == 60
        assert self.plugin.get_interval_seconds("1h") == 3600
        assert self.plugin.get_interval_seconds("1d") == 86400
        
        # Default for unknown interval
        assert self.plugin.get_interval_seconds("unknown") == 60
        
    @pytest.mark.asyncio
    async def test_handle_rest_candles_request(self):
        """Test handling REST API candles requests."""
        # Test with minimal parameters
        params = {"symbol": "BTC-USDT"}
        response = await self.plugin.handle_rest_candles_request(params)
        
        # Verify response structure
        assert response["status"] == "ok"
        assert response["symbol"] == "BTC-USDT"
        assert response["interval"] == "1m"  # Default interval
        assert isinstance(response["data"], list)
        assert len(response["data"]) == 500  # Default limit
        
        # Test with all parameters
        params = {"symbol": "ETH-USDT", "interval": "5m", "limit": "10"}
        response = await self.plugin.handle_rest_candles_request(params)
        
        # Verify response
        assert response["status"] == "ok"
        assert response["symbol"] == "ETH-USDT"
        assert response["interval"] == "5m"
        assert len(response["data"]) == 10
        
        # Verify candle data structure
        first_candle = response["data"][0]
        assert "timestamp" in first_candle
        assert "open" in first_candle
        assert "high" in first_candle
        assert "low" in first_candle
        assert "close" in first_candle
        assert "volume" in first_candle
        assert "quote_volume" in first_candle
        
        # Verify timestamps are in ascending order (oldest first)
        timestamps = [int(candle["timestamp"]) for candle in response["data"]]
        assert timestamps == sorted(timestamps)
        
    @pytest.mark.asyncio
    async def test_handle_ws_connection(self):
        """Test handling WebSocket connections."""
        # Create mock websocket
        mock_ws = AsyncMock()
        mock_ws.receive_json.return_value = {
            "type": "subscribe",
            "subscriptions": [
                {"symbol": "BTC-USDT", "interval": "1m"}
            ]
        }
        
        # Test handling connection
        await self.plugin.handle_ws_connection(mock_ws)
        
        # Verify subscription confirmation was sent
        mock_ws.send_json.assert_any_call({
            "status": "subscribed",
            "subscriptions": [
                {"symbol": "BTC-USDT", "interval": "1m"}
            ]
        })
        
        # Verify candle update was sent
        assert mock_ws.send_json.call_count == 2
        
        # Get the second call arguments (candle update)
        candle_update_call = mock_ws.send_json.call_args_list[1]
        candle_update = candle_update_call[0][0]
        
        # Verify candle update structure
        assert candle_update["type"] == "candle_update"
        assert candle_update["symbol"] == "BTC-USDT"
        assert candle_update["interval"] == "1m"
        assert "data" in candle_update
        
        # Verify candle data structure
        candle_data = candle_update["data"]
        assert "timestamp" in candle_data
        assert "open" in candle_data
        assert "high" in candle_data
        assert "low" in candle_data
        assert "close" in candle_data
        assert "volume" in candle_data
        assert "quote_volume" in candle_data