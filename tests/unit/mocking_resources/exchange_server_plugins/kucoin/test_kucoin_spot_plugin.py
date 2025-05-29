"""
Unit tests for the KucoinSpotPlugin class.
"""

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.kucoin.spot_plugin import (
    KucoinSpotPlugin,
)


class TestKucoinSpotPlugin:
    """Test suite for the KucoinSpotPlugin."""

    def setup_method(self):
        """Set up the test."""
        self.plugin = KucoinSpotPlugin()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.KUCOIN_SPOT
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url.startswith("wss://")
        assert "/ws" in self.plugin.ws_routes

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        assert "/api/v1/market/candles" in routes
        assert routes["/api/v1/market/candles"][0] == "GET"
        assert routes["/api/v1/market/candles"][1] == "handle_klines"

    @pytest.mark.asyncio
    async def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with query parameters
        from aiohttp.test_utils import make_mocked_request

        request = make_mocked_request(
            "GET",
            "/api/v1/market/candles?symbol=BTC-USDT&type=1min&startAt=1620000000&endAt=1620100000&limit=100",
            headers={},
        )

        # Parse parameters
        params = self.plugin.parse_rest_candles_params(request)

        # Check parsed parameters
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert params["limit"] == 100
        assert params["start_time"] == "1620000000"
        assert params["end_time"] == "1620100000"

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
        assert formatted["code"] == "200000"
        assert "data" in formatted
        assert len(formatted["data"]) == 1
        assert formatted["data"][0][0] == 1620000000000  # Timestamp in milliseconds
        assert formatted["data"][0][1] == str(candles[0].open)  # Open
        assert formatted["data"][0][2] == str(candles[0].close)  # Close
        assert formatted["data"][0][3] == str(candles[0].high)  # High
        assert formatted["data"][0][4] == str(candles[0].low)  # Low
        assert formatted["data"][0][5] == str(candles[0].volume)  # Volume
        assert formatted["data"][0][6] == str(candles[0].quote_asset_volume)  # Quote volume

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
        assert message["type"] == "message"
        assert message["topic"].startswith("/market/candles:")
        assert "BTC-USDT_1min" in message["topic"]
        assert message["subject"] == "trade.candles.update"
        assert message["data"]["symbol"] == "BTC-USDT"
        assert message["data"]["candles"][0] == str(1620000000000)  # Timestamp
        assert message["data"]["candles"][1] == str(candle.open)  # Open
        assert message["data"]["candles"][2] == str(candle.close)  # Close
        assert message["data"]["candles"][3] == str(candle.high)  # High
        assert message["data"]["candles"][4] == str(candle.low)  # Low
        assert message["data"]["candles"][5] == str(candle.volume)  # Volume
        assert message["data"]["candles"][6] == str(candle.quote_asset_volume)  # Quote volume

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message
        message = {
            "id": "12345",
            "type": "subscribe",
            "topic": "/market/candles:BTC-USDT_1min",
            "privateChannel": False,
            "response": True
        }

        # Parse subscription
        subscriptions = self.plugin.parse_ws_subscription(message)

        # Check parsed subscriptions
        assert len(subscriptions) == 1
        assert subscriptions[0][0] == "BTC-USDT"
        assert subscriptions[0][1] == "1m"

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        # Create subscription message
        message = {
            "id": "12345",
            "type": "subscribe",
            "topic": "/market/candles:BTC-USDT_1min",
            "privateChannel": False,
            "response": True
        }

        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USDT", "1m")])

        # Check response format
        assert response["id"] == "12345"
        assert response["type"] == "ack"

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")

        # Check key format
        assert key == "/market/candles:BTC-USDT_1min"
