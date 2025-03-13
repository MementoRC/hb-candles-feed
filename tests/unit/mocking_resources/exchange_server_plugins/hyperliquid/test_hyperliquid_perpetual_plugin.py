"""
Unit tests for the HyperliquidPerpetualPlugin class.
"""

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.hyperliquid.perpetual_plugin import HyperliquidPerpetualPlugin


class TestHyperliquidPerpetualPlugin:
    """Test suite for the HyperliquidPerpetualPlugin."""

    def setup_method(self):
        """Set up the test."""
        self.plugin = HyperliquidPerpetualPlugin()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.HYPERLIQUID_PERPETUAL
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url.startswith("wss://")
        assert "/ws" in self.plugin.ws_routes

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        assert "/info" in routes
        assert routes["/info"][0] == "POST"
        assert routes["/info"][1] == "handle_klines"

    @pytest.mark.asyncio
    async def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with JSON body
        from aiohttp.test_utils import make_mocked_request
        
        request = make_mocked_request(
            "POST", 
            "/info",
            headers={"Content-Type": "application/json"},
        )
        
        # Mock the request to have a JSON body
        request._read_bytes = b'{"type":"candles","coin":"BTC","resolution":"1","limit":100,"startTime":1620000000,"endTime":1620100000}'
        
        # Parse parameters
        params = await self.plugin.parse_rest_candles_params(request)
        
        # Check parsed parameters
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert params["limit"] == 100
        assert params["start_time"] == 1620000000
        assert params["end_time"] == 1620100000

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
        assert isinstance(formatted, list)
        assert len(formatted) == 1
        assert formatted[0][0] == 1620000000  # Timestamp in seconds
        assert formatted[0][1] == 50000.0  # Open
        assert formatted[0][2] == 51000.0  # High
        assert formatted[0][3] == 49000.0  # Low
        assert formatted[0][4] == 50500.0  # Close
        assert formatted[0][5] == 10.5  # Volume
        assert formatted[0][6] == 525000.0  # Quote volume

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
        assert message["channel"] == "candles"
        assert message["coin"] == "BTC"  # Only the base asset
        assert message["interval"] == "1"  # Converted from 1m to 60
        assert message["data"][0] == 1620000000  # Timestamp in seconds
        assert message["data"][1] == 50000.0  # Open
        assert message["data"][2] == 51000.0  # High
        assert message["data"][3] == 49000.0  # Low
        assert message["data"][4] == 50500.0  # Close
        assert message["data"][5] == 10.5  # Volume
        assert message["data"][6] == 525000.0  # Quote volume

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message
        message = {
            "method": "subscribe",
            "channel": "candles",
            "coin": "BTC",
            "interval": "1"
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
            "method": "subscribe",
            "channel": "candles",
            "coin": "BTC",
            "interval": "1"
        }
        
        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USDT", "1m")])
        
        # Check response format
        assert response["success"] is True
        assert "message" in response

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")
        
        # Check key format
        assert key == "BTC:1"  # Base asset and interval in seconds