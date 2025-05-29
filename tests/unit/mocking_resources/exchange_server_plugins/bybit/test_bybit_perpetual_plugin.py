"""
Unit tests for the BybitPerpetualPlugin class.
"""

import pytest

from candles_feed.adapters.bybit.constants import PERPETUAL_WSS_URL
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.bybit.perpetual_plugin import (
    BybitPerpetualPlugin,
)


class TestBybitPerpetualPlugin:
    """Test suite for the BybitPerpetualPlugin."""

    def setup_method(self):
        """Set up the test."""
        self.plugin = BybitPerpetualPlugin()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.BYBIT_PERPETUAL
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url == PERPETUAL_WSS_URL
        assert "/ws" in self.plugin.ws_routes

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        assert "/v5/market/kline" in routes
        assert routes["/v5/market/kline"][0] == "GET"
        assert routes["/v5/market/kline"][1] == "handle_klines"
        assert "/v5/market/time" in routes
        assert "/v5/market/instruments-info" in routes

    @pytest.mark.asyncio
    async def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with query parameters
        from aiohttp.test_utils import make_mocked_request

        request = make_mocked_request(
            "GET",
            "/v5/market/kline?symbol=BTCUSDT&interval=1&start=1620000000000&end=1620100000000&limit=100&category=linear",
            headers={},
        )

        # Parse parameters
        params = self.plugin.parse_rest_candles_params(request)

        # Check parsed parameters
        assert params["symbol"] == "BTCUSDT"
        assert params["interval"] == "1"
        assert params["limit"] == 100
        assert params["start_time"] == "1620000000000"
        assert params["end_time"] == "1620100000000"
        assert params["category"] == "linear"

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
        assert formatted["retCode"] == 0
        assert formatted["retMsg"] == "OK"
        assert formatted["result"]["category"] == "linear"  # Perpetual uses "linear" category
        assert formatted["result"]["symbol"] == "BTCUSDT"

        # Check the first candle
        assert len(formatted["result"]["list"]) == 1
        candle_data = formatted["result"]["list"][0]
        assert candle_data[0] == str(int(candles[0].timestamp_ms))  # Timestamp in ms
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
        assert message["topic"] == "kline.1.BTCUSDT"  # Interval maps from 1m to 1
        assert message["ts"] == int(candle.timestamp_ms)
        assert message["type"] == "snapshot"

        # Check data field
        assert len(message["data"]) == 1
        data = message["data"][0]
        assert data["start"] == int(candle.timestamp_ms)
        assert data["end"] > int(candle.timestamp_ms)  # End time is start + interval
        assert data["interval"] == "1"  # Mapped from 1m
        assert data["open"] == str(candle.open)
        assert data["close"] == str(candle.close)
        assert data["high"] == str(candle.high)
        assert data["low"] == str(candle.low)
        assert data["volume"] == str(candle.volume)
        assert data["turnover"] == str(candle.quote_asset_volume)
        assert data["confirm"] is False  # Default to not final

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message
        message = {
            "op": "subscribe",
            "args": [
                "kline.1.BTCUSDT"
            ],
            "req_id": 12345
        }

        # Parse subscription
        subscriptions = self.plugin.parse_ws_subscription(message)

        # Check parsed subscriptions
        assert len(subscriptions) == 1
        assert subscriptions[0][0] == "BTC-USDT"  # Trading pair should be reformatted
        assert subscriptions[0][1] == "1m"        # Interval should be mapped back to standard format

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        # Create subscription message
        message = {
            "op": "subscribe",
            "args": [
                "kline.1.BTCUSDT"
            ],
            "req_id": 12345
        }

        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USDT", "1m")])

        # Check response format
        assert response["success"] is True
        assert response["ret_msg"] == "subscribe success"
        assert response["op"] == "subscribe"
        assert response["args"] == ["kline.1.BTCUSDT"]

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")

        # Check key format
        assert key == "kline.1.BTCUSDT"  # Should map 1m to 1 and remove hyphen
