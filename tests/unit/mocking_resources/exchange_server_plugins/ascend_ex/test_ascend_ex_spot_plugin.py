"""
Unit tests for the AscendExSpotPlugin class.
"""

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.ascend_ex.spot_plugin import (
    AscendExSpotPlugin,
)


class TestAscendExSpotPlugin:
    """Test suite for the AscendExSpotPlugin."""

    def setup_method(self):
        """Set up the test."""
        self.plugin = AscendExSpotPlugin()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.ASCEND_EX_SPOT
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url.startswith("wss://")
        assert "/api/pro/v1/websocket-for-hummingbot-liq-mining/stream" in self.plugin.ws_routes

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        assert "/api/pro/v1/barhist" in routes
        assert routes["/api/pro/v1/barhist"][0] == "GET"
        assert routes["/api/pro/v1/barhist"][1] == "handle_klines"
        assert "/api/pro/v1/products" in routes

    def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with query parameters
        from aiohttp.test_utils import make_mocked_request

        request = make_mocked_request(
            "GET",
            "/api/pro/v1/barhist?symbol=BTC/USDT&interval=1&n=100&to=1620100000000",
            headers={},
        )

        # Parse parameters
        params = self.plugin.parse_rest_candles_params(request)

        # Check parsed parameters
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert params["limit"] == 100
        assert params["end_time"] == "1620100000000"

    def test_format_rest_candles(self):
        """Test formatting REST API candle response."""
        # Create sample candle data
        candles = [
            CandleData(
                timestamp_raw=1620000000000,
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
        assert formatted["code"] == 0
        assert "data" in formatted
        assert len(formatted["data"]) == 1

        # Check first candle
        candle_data = formatted["data"][0]
        assert candle_data["m"] == "bar"
        assert candle_data["s"] == "BTC/USDT"
        assert "data" in candle_data
        assert candle_data["data"]["ts"] == 1620000000000
        assert candle_data["data"]["o"] == str(candles[0].open)
        assert candle_data["data"]["h"] == str(candles[0].high)
        assert candle_data["data"]["l"] == str(candles[0].low)
        assert candle_data["data"]["c"] == str(candles[0].close)
        assert candle_data["data"]["v"] == str(candles[0].quote_asset_volume)

    def test_format_ws_candle_message(self):
        """Test formatting WebSocket candle message."""
        # Create sample candle data
        candle = CandleData(
            timestamp_raw=1620000000000,
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
        assert message["m"] == "bar"
        assert message["s"] == "BTC/USDT"
        assert "data" in message
        assert message["data"]["ts"] == 1620000000000
        assert message["data"]["o"] == str(candle.open)
        assert message["data"]["h"] == str(candle.high)
        assert message["data"]["l"] == str(candle.low)
        assert message["data"]["c"] == str(candle.close)
        assert message["data"]["v"] == str(candle.quote_asset_volume)

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message
        message = {"op": "sub", "ch": "bar:1:BTC/USDT"}

        # Parse subscription
        subscriptions = self.plugin.parse_ws_subscription(message)

        # Check parsed subscriptions
        assert len(subscriptions) == 1
        assert subscriptions[0][0] == "BTC-USDT"
        assert subscriptions[0][1] == "1m"

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        # Create subscription message
        message = {"op": "sub", "ch": "bar:1:BTC/USDT", "id": "12345"}

        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USDT", "1m")])

        # Check response format
        assert response["m"] == "sub"
        assert response["id"] == "12345"
        assert response["code"] == 0

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")

        # Check key format
        assert key == "bar:1:BTC/USDT"

    @pytest.mark.asyncio
    async def test_handle_instruments(self):
        """Test handling instruments endpoint."""
        from unittest.mock import AsyncMock, MagicMock

        # Create mocks
        mock_server = MagicMock()
        mock_server._simulate_network_conditions = AsyncMock()
        mock_server._check_rate_limit = MagicMock(return_value=True)
        mock_server.trading_pairs = {"BTC-USDT": 50000.0, "ETH-USDT": 3000.0}

        # Create mock request
        mock_request = MagicMock()
        mock_request.remote = "127.0.0.1"

        # Call the method
        response = await self.plugin.handle_instruments(mock_server, mock_request)

        # Check if server methods were called
        mock_server._simulate_network_conditions.assert_called_once()
        mock_server._check_rate_limit.assert_called_once_with("127.0.0.1", "rest")

        # Response should not be None
        assert response is not None
