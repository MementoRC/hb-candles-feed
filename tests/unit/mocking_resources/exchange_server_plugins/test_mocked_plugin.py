"""
Unit tests for the MockedPlugin class.
"""

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin import MockedPlugin


class TestMockedPlugin:
    """Test suite for the MockedPlugin."""

    def setup_method(self):
        """Set up the test."""
        self.plugin = MockedPlugin()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.MOCK
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url.startswith("wss://")
        assert "/ws" in self.plugin.ws_routes

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        assert "/api/candles" in routes
        assert routes["/api/candles"][0] == "GET"
        assert routes["/api/candles"][1] == "handle_klines"
        assert "/api/time" in routes
        assert "/api/instruments" in routes

    @pytest.mark.asyncio
    async def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with query parameters
        from aiohttp.test_utils import make_mocked_request

        request = make_mocked_request(
            "GET",
            "/api/candles?symbol=BTC-USDT&interval=1m&limit=100&start_time=1620000000000&end_time=1620100000000",
            headers={},
        )

        # Parse parameters
        params = self.plugin.parse_rest_candles_params(request)

        # Check parsed parameters
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert params["limit"] == 100
        assert params["start_time"] == "1620000000000"
        assert params["end_time"] == "1620100000000"

    def test_format_rest_candles(self):
        """Test formatting REST API candle response."""
        # Create sample candle data
        candles = [
            CandleData(
                timestamp_raw=1620000000,
                open=50000.0,
                high=51000.0,
                low=49000.0,
                close=50500.0,
                volume=10.5,
                quote_asset_volume=525000.0,
                n_trades=100,
                taker_buy_base_volume=5.25,
                taker_buy_quote_volume=262500.0,
            )
        ]

        # Format candles
        formatted = self.plugin.format_rest_candles(candles, self.trading_pair, self.interval)

        # Check formatted data
        assert isinstance(formatted, dict)
        assert formatted["status"] == "ok"
        assert formatted["symbol"] == self.trading_pair
        assert formatted["interval"] == self.interval
        assert isinstance(formatted["data"], list)

        # Check the first candle
        candle_data = formatted["data"][0]
        assert candle_data["timestamp"] == int(candles[0].timestamp_ms)
        assert candle_data["open"] == str(candles[0].open)
        assert candle_data["high"] == str(candles[0].high)
        assert candle_data["low"] == str(candles[0].low)
        assert candle_data["close"] == str(candles[0].close)
        assert candle_data["volume"] == str(candles[0].volume)
        assert candle_data["quote_volume"] == str(candles[0].quote_asset_volume)

    def test_format_ws_candle_message(self):
        """Test formatting WebSocket candle message."""
        # Create sample candle data
        candle = CandleData(
            timestamp_raw=1620000000,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=10.5,
            quote_asset_volume=525000.0,
            n_trades=100,
            taker_buy_base_volume=5.25,
            taker_buy_quote_volume=262500.0,
        )

        # Format WebSocket message
        message = self.plugin.format_ws_candle_message(candle, self.trading_pair, self.interval)

        # Check message format
        assert isinstance(message, dict)
        assert message["type"] == "candle_update"
        assert message["symbol"] == self.trading_pair
        assert message["interval"] == self.interval
        assert isinstance(message["is_final"], bool)

        # Check data field
        data = message["data"]
        assert data["timestamp"] == int(candle.timestamp_ms)
        assert data["open"] == str(candle.open)
        assert data["high"] == str(candle.high)
        assert data["low"] == str(candle.low)
        assert data["close"] == str(candle.close)
        assert data["volume"] == str(candle.volume)
        assert data["quote_volume"] == str(candle.quote_asset_volume)

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message
        message = {"type": "subscribe", "subscriptions": [{"symbol": "BTC-USDT", "interval": "1m"}]}

        # Parse subscription
        subscriptions = self.plugin.parse_ws_subscription(message)

        # Check parsed subscriptions
        assert len(subscriptions) == 1
        assert subscriptions[0][0] == "BTC-USDT"
        assert subscriptions[0][1] == "1m"

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        # Create subscription message
        message = {"type": "subscribe", "subscriptions": [{"symbol": "BTC-USDT", "interval": "1m"}]}

        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USDT", "1m")])

        # Check response format
        assert response["type"] == "subscribe_result"
        assert response["status"] == "success"
        assert isinstance(response["subscriptions"], list)
        assert len(response["subscriptions"]) == 1
        assert response["subscriptions"][0]["symbol"] == "BTC-USDT"
        assert response["subscriptions"][0]["interval"] == "1m"

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")

        # Check key format
        assert key == "BTC-USDT_1m"

    def test_parse_rest_candles_params_with_invalid_limit(self):
        """Test parsing REST API parameters with invalid limit value."""
        from aiohttp.test_utils import make_mocked_request

        # Create a request with an invalid limit parameter
        request = make_mocked_request(
            "GET",
            "/api/candles?symbol=BTC-USDT&interval=1m&limit=invalid",
            headers={},
        )

        # Parse parameters
        params = self.plugin.parse_rest_candles_params(request)

        # Check that limit has been set to a default value
        assert isinstance(params["limit"], int)
        assert params["limit"] == 1000  # Default value from our implementation
