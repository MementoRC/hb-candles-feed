"""
Unit tests for MockedPlugin.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import web as aiohttp_web  # For WSMsgType

from candles_feed.core.candle_data import CandleData
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
    async def test_handle_klines(self):
        """Test handling klines (candles) REST API requests."""
        mock_server = Mock()
        mock_server._simulate_network_conditions = AsyncMock()
        mock_server._check_rate_limit = Mock(return_value=True)

        # Populate server.candles with some data
        btc_candles = [
            CandleData(
                timestamp_raw=1678886400 + i * 60,
                open=50000 + i,
                high=50100 + i,
                low=49900 + i,
                close=50050 + i,
                volume=10.0 + i,
                quote_asset_volume=500000.0 + i * 100,
            )
            for i in range(600)  # Create 600 candles for BTC-USDT
        ]
        eth_candles = [
            CandleData(
                timestamp_raw=1678886400 + i * 300,
                open=3000 + i,
                high=3010 + i,
                low=2990 + i,
                close=3005 + i,
                volume=100.0 + i,
                quote_asset_volume=300000.0 + i * 100,
            )
            for i in range(20)  # Create 20 candles for ETH-USDT
        ]
        mock_server.candles = {
            "BTC-USDT": {"1m": btc_candles},
            "ETH-USDT": {"5m": eth_candles},
        }

        # Test with minimal parameters (symbol and interval, limit defaults to 1000)
        mock_request_1 = Mock()
        mock_request_1.query = {
            "symbol": "BTCUSDT",
            "interval": "1m",
        }  # Use "BTCUSDT" to test symbol normalization
        mock_request_1.remote = "127.0.0.1"

        web_response_1 = await self.plugin.handle_klines(mock_server, mock_request_1)
        assert web_response_1.status == 200
        response_1_json = json.loads(web_response_1.text)

        # Verify response structure
        assert response_1_json["status"] == "ok"
        assert (
            response_1_json["symbol"] == "BTC-USDT"
        )  # Symbol in response is the key from server.candles
        assert response_1_json["interval"] == "1m"
        assert isinstance(response_1_json["data"], list)
        assert len(response_1_json["data"]) == 600  # Default limit is 1000, but only 600 available

        # Test with all parameters
        mock_request_2 = Mock()
        mock_request_2.query = {"symbol": "ETH-USDT", "interval": "5m", "limit": "10"}
        mock_request_2.remote = "127.0.0.1"

        web_response_2 = await self.plugin.handle_klines(mock_server, mock_request_2)
        assert web_response_2.status == 200
        response_2_json = json.loads(web_response_2.text)

        # Verify response
        assert response_2_json["status"] == "ok"
        assert response_2_json["symbol"] == "ETH-USDT"
        assert response_2_json["interval"] == "5m"
        assert len(response_2_json["data"]) == 10  # 20 available, limit is 10

        # Verify candle data structure from the second response
        assert len(response_2_json["data"]) > 0
        first_candle = response_2_json["data"][0]
        assert "timestamp" in first_candle
        assert "open" in first_candle
        assert "high" in first_candle
        assert "low" in first_candle
        assert "close" in first_candle
        assert "volume" in first_candle
        assert "quote_volume" in first_candle
        assert "close_time" in first_candle  # Added by format_rest_candles
        assert "trades" in first_candle
        assert "taker_base_volume" in first_candle
        assert "taker_quote_volume" in first_candle

        # Verify timestamps are in ascending order (oldest first)
        # Data is taken from the end of the list by mock server, so it's already sorted if source is sorted.
        timestamps = [int(candle["timestamp"]) for candle in response_2_json["data"]]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    @patch(
        "candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin.web.WebSocketResponse"
    )
    async def test_handle_websocket(self, mock_websocket_response):
        """Test handling WebSocket connections and subscriptions."""
        # Configure the mock WebSocket instance that mock_websocket_response will return
        mock_ws_instance = AsyncMock()
        mock_ws_instance.prepare = AsyncMock()
        mock_ws_instance.send_json = AsyncMock()
        mock_ws_instance.closed = False
        mock_ws_instance.exception = Mock(return_value=None)

        # Simulate receiving one subscription message
        # Set up async iteration properly - yield message then wait indefinitely
        # We'll cancel this by stopping the async iteration after we verify the state
        message_yielded = False
        
        async def mock_receive_messages():
            nonlocal message_yielded
            yield Mock(
                type=aiohttp_web.WSMsgType.TEXT,
                data=json.dumps(
                    {
                        "type": "subscribe",
                        "subscriptions": [
                            # Use "BTCUSDT" to test if plugin handles unnormalized symbols in request
                            # but normalizes for internal use and candle messages.
                            {"symbol": "BTCUSDT", "interval": "1m"}
                        ],
                    }
                ),
            )
            message_yielded = True
            # Wait indefinitely to keep connection "alive" for subscription verification
            # We'll need to manually break this loop in the test
            while True:
                await asyncio.sleep(0.1)

        mock_ws_instance.__aiter__ = lambda self: mock_receive_messages()

        # Configure the patched class to return our mock instance
        mock_websocket_response.return_value = mock_ws_instance

        # Setup mock_server - use real dict/set for collections
        mock_server = Mock()
        mock_server.latency_ms = 0
        mock_server._check_rate_limit = Mock(return_value=True)
        # Use real collections, not Mock objects
        real_ws_connections = set()
        real_subscriptions = {}
        mock_server.ws_connections = real_ws_connections
        mock_server.subscriptions = real_subscriptions
        mock_server.logger = Mock()

        # Populate server.candles with data for the subscription
        candle_obj = CandleData(
            timestamp_raw=1678886400,
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=10.0,
            quote_asset_volume=500000.0,
        )
        mock_server.candles = {
            "BTC-USDT": {"1m": [candle_obj]}  # Plugin uses normalized "BTC-USDT" as key
        }

        # Setup mock_request
        mock_request = Mock()
        mock_request.remote = "127.0.0.1"

        # Call the method under test in a task so we can inspect state while it's running
        import asyncio
        handler_task = asyncio.create_task(self.plugin.handle_websocket(mock_server, mock_request))
        
        # Wait for the message to be processed and subscription to be added
        for _ in range(50):  # Wait up to 5 seconds
            await asyncio.sleep(0.1)
            if message_yielded and len(mock_ws_instance.send_json.call_args_list) >= 2:
                break
        
        # Capture the subscription state while the connection is still "active"
        # (before canceling the task, which triggers cleanup)
        subscription_key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")
        subscription_exists = subscription_key in mock_server.subscriptions
        subscription_count = len(mock_server.subscriptions.get(subscription_key, set()))
        
        # Cancel the handler task
        handler_task.cancel()
        try:
            await handler_task
        except asyncio.CancelledError:
            pass

        # --- Assertions ---

        # 1. WebSocketResponse was instantiated and prepared
        mock_websocket_response.assert_called_once()
        mock_ws_instance.prepare.assert_called_once_with(mock_request)

        # 2. Subscription success message
        # Plugin uses the symbol from the request ("BTCUSDT") in the success message for "our format"
        expected_subscription_success = {
            "type": "subscribe_result",
            "status": "success",
            "subscriptions": [{"symbol": "BTCUSDT", "interval": "1m"}],
        }

        # 3. Candle update message
        # Plugin uses the normalized symbol ("BTC-USDT") from server.candles for the candle data message
        expected_candle_data_payload = {
            "timestamp": int(candle_obj.timestamp_ms),
            "open": str(candle_obj.open),
            "high": str(candle_obj.high),
            "low": str(candle_obj.low),
            "close": str(candle_obj.close),
            "volume": str(candle_obj.volume),
            "quote_volume": str(candle_obj.quote_asset_volume),
        }
        expected_candle_update = {
            "type": "candle_update",
            "symbol": "BTC-USDT",  # Normalized symbol
            "interval": "1m",
            "is_final": True,  # Initial candle is marked as final
            "data": expected_candle_data_payload,
        }

        # Check the calls to send_json
        calls = mock_ws_instance.send_json.call_args_list
        assert len(calls) == 2, (
            "Expected two messages: subscription confirmation and one candle update."
        )

        # First call: subscription success
        assert calls[0][0][0] == expected_subscription_success
        # Second call: candle update (after a small delay in the handler)
        assert calls[1][0][0] == expected_candle_update

        # 4. Verify server state (subscription tracking)
        # Subscription key uses the normalized pair ("BTC-USDT")
        assert subscription_exists, f"Subscription key {subscription_key} was not found in server.subscriptions"
        
        # Verify that subscription tracking is working properly
        assert subscription_count == 1, f"Expected 1 subscription, got {subscription_count}"
