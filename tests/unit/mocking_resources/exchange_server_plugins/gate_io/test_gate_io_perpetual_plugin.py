"""
Unit tests for the GateIoPerpetualPlugin class.
"""

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.gate_io.perpetual_plugin import (
    GateIoPerpetualPlugin,
)


class TestGateIoPerpetualPlugin:
    """Test suite for the GateIoPerpetualPlugin."""

    def setup_method(self):
        """Set up the test."""
        self.plugin = GateIoPerpetualPlugin()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.GATE_IO_PERPETUAL
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url.startswith("wss://")
        assert "/ws/v4" in self.plugin.ws_routes

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        assert "/api/v4/futures/usdt/candlesticks" in routes
        assert routes["/api/v4/futures/usdt/candlesticks"][0] == "GET"
        assert routes["/api/v4/futures/usdt/candlesticks"][1] == "handle_klines"

    @pytest.mark.asyncio
    async def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with query parameters
        from aiohttp.test_utils import make_mocked_request

        request = make_mocked_request(
            "GET",
            "/api/v4/futures/usdt/candlesticks?currency_pair=BTC_USDT&interval=1m&limit=100&from=1620000000&to=1620100000",
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
        assert formatted[0][0] == "1620000000"  # Timestamp in seconds as string
        assert formatted[0][1] == str(candles[0].open)  # Open
        assert formatted[0][2] == str(candles[0].close)  # Close
        assert formatted[0][3] == str(candles[0].low)  # Low
        assert formatted[0][4] == str(candles[0].high)  # High
        assert formatted[0][5] == str(candles[0].volume)  # Volume
        assert formatted[0][6] == str(candles[0].quote_asset_volume)  # Quote volume
        assert formatted[0][7] == "BTC_USDT"  # Trading pair

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
        assert message["time"] == 1620000000  # Timestamp in seconds
        assert message["channel"] == "futures.candlesticks"  # Different channel for perpetual
        assert message["event"] == "update"
        assert message["result"]["t"] == "1620000000"
        assert message["result"]["o"] == str(candle.open)
        assert message["result"]["c"] == str(candle.close)
        assert message["result"]["h"] == str(candle.high)
        assert message["result"]["l"] == str(candle.low)
        assert message["result"]["n"] == "BTC_USDT"

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message
        message = {
            "method": "subscribe",
            "params": ["futures.candlesticks", {"currency_pair": "BTC_USDT", "interval": "1m"}],
            "id": 12345,
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
            "params": ["futures.candlesticks", {"currency_pair": "BTC_USDT", "interval": "1m"}],
            "id": 12345,
        }

        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USDT", "1m")])

        # Check response format
        assert response["id"] == 12345
        assert response["result"]["status"] == "success"
        assert response["error"] is None

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")

        # Check key format
        assert key == "BTC_USDT_1m"
