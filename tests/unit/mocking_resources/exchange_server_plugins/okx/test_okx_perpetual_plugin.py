"""
Unit tests for the OKXPerpetualPlugin class.
"""

import pytest
import aiohttp
from aiohttp import web
from typing import Any

from candles_feed.adapters.okx.constants import INTERVAL_TO_EXCHANGE_FORMAT
from candles_feed.adapters.okx.perpetual_adapter import OKXPerpetualAdapter
from candles_feed.mocking_resources.exchange_server_plugins.okx.perpetual_plugin import OKXPerpetualPlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.exchange_server_plugins.okx.base_plugin import OKXBasePlugin


class TestOKXPerpetualPlugin:
    """Test suite for the OKXPerpetualPlugin."""

    def setup_method(self):
        """Set up the test."""
        # Note: The constructor signature is inconsistent with other plugins in the actual implementation
        # In a real scenario we would fix the implementation, but for testing we adapt to current code
        self.plugin = OKXPerpetualPlugin(ExchangeType.OKX_PERPETUAL)
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.OKX_PERPETUAL
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url.startswith("wss://")
        assert "/ws/v5/public" in self.plugin.ws_routes

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        assert "/api/v5/market/history-candles" in routes  # Different endpoint for perpetual
        assert routes["/api/v5/market/history-candles"][0] == "GET"
        assert routes["/api/v5/market/history-candles"][1] == "handle_klines"
        assert "/api/v5/public/time" in routes
        assert "/api/v5/public/instruments" in routes

    @pytest.mark.asyncio
    async def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with query parameters
        from aiohttp.test_utils import make_mocked_request
        
        request = make_mocked_request(
            "GET", 
            "/api/v5/market/history-candles?instId=BTC-USDT&bar=1m&limit=100&after=1620000000000&before=1620100000000",
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
        
        # Check original parameters are preserved
        assert params["instId"] == "BTC-USDT"
        assert params["bar"] == "1m"
        assert params["after"] == "1620000000000"
        assert params["before"] == "1620100000000"

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
        assert formatted["code"] == "0"
        assert formatted["msg"] == ""
        assert len(formatted["data"]) == 1
        
        # Check the first candle
        candle_data = formatted["data"][0]
        assert candle_data[0] == str(int(candles[0].timestamp_ms))  # Timestamp in ms as string
        assert candle_data[1] == str(candles[0].open)              # Open
        assert candle_data[2] == str(candles[0].high)              # High
        assert candle_data[3] == str(candles[0].low)               # Low
        assert candle_data[4] == str(candles[0].close)             # Close
        assert candle_data[5] == str(candles[0].volume)            # Volume
        assert candle_data[6] == str(candles[0].quote_asset_volume)  # Quote volume

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
        assert "arg" in message
        assert "data" in message
        
        # Check arg field
        assert message["arg"]["channel"] == f"candle{INTERVAL_TO_EXCHANGE_FORMAT.get('1m', '1m')}"
        assert message["arg"]["instId"] == self.trading_pair
        
        # Check data field
        assert len(message["data"]) == 1
        candle_data = message["data"][0]
        assert candle_data[0] == str(int(candle.timestamp_ms))  # Timestamp
        assert candle_data[1] == str(candle.open)               # Open
        assert candle_data[2] == str(candle.high)               # High
        assert candle_data[3] == str(candle.low)                # Low
        assert candle_data[4] == str(candle.close)              # Close
        assert candle_data[5] == str(candle.volume)             # Volume
        assert candle_data[6] == str(candle.quote_asset_volume) # Quote volume

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message in OKX format
        message = {
            "op": "subscribe",
            "args": [
                {
                    "channel": "candle1m",
                    "instId": "BTC-USDT"
                }
            ]
        }
        
        # Parse subscription
        subscriptions = self.plugin.parse_ws_subscription(message)
        
        # Check parsed subscriptions
        assert len(subscriptions) == 1
        assert subscriptions[0][0] == "BTC-USDT"  # Trading pair
        assert subscriptions[0][1] == "1m"        # Interval

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        # Create subscription message
        message = {
            "op": "subscribe",
            "args": [
                {
                    "channel": "candle1m",
                    "instId": "BTC-USDT"
                }
            ]
        }
        
        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USDT", "1m")])
        
        # Check response format
        assert response["event"] == "subscribe"
        assert response["arg"] == message["args"][0]
        assert response["code"] == "0"
        assert response["msg"] == "OK"

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")
        
        # Check key format
        interval_code = INTERVAL_TO_EXCHANGE_FORMAT.get("1m", "1m")
        assert key == f"candle{interval_code}_BTC-USDT"

    def test_interval_to_seconds(self):
        """Test converting interval to seconds."""
        # Test various intervals
        assert OKXBasePlugin._interval_to_seconds("1s") == 1
        assert OKXBasePlugin._interval_to_seconds("1m") == 60
        assert OKXBasePlugin._interval_to_seconds("1h") == 3600
        assert OKXBasePlugin._interval_to_seconds("1d") == 86400
        assert OKXBasePlugin._interval_to_seconds("1w") == 604800
        
        # Test with different values
        assert OKXBasePlugin._interval_to_seconds("5m") == 300
        assert OKXBasePlugin._interval_to_seconds("4h") == 14400
        
        # Test invalid interval
        with pytest.raises(ValueError):
            OKXBasePlugin._interval_to_seconds("1x")