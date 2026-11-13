"""
Unit tests for the CoinbaseAdvancedTradeSpotPlugin class.
"""

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.server import MockedExchangeServer
from candles_feed.mocking_resources.exchange_server_plugins.coinbase_advanced_trade.spot_plugin import (
    CoinbaseAdvancedTradeSpotPlugin,
)


class TestCoinbaseAdvancedTradeSpotPlugin:
    """Test suite for the CoinbaseAdvancedTradeSpotPlugin."""

    def setup_method(self):
        """Set up the test."""
        self.plugin = CoinbaseAdvancedTradeSpotPlugin()
        self.trading_pair = "BTC-USD"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.COINBASE_ADVANCED_TRADE
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url.startswith("wss://")
        assert "/" in self.plugin.ws_routes

    def test_interval_to_seconds(self):
        """Test interval conversion; unknown units are rejected."""
        assert self.plugin._interval_to_seconds("1h") == 3600
        assert self.plugin._interval_to_seconds("5m") == 300
        with pytest.raises(ValueError, match="Unknown interval unit"):
            self.plugin._interval_to_seconds("5x")

    def test_normalize_trading_pair(self):
        """Pairs without a separator get one before the quote currency."""
        assert self.plugin.normalize_trading_pair("BTC-USD") == "BTC-USD"
        assert self.plugin.normalize_trading_pair("BTCUSD") == "BTC-USD"
        assert self.plugin.normalize_trading_pair("ethusdt") == "ETH-USDT"

    def test_server_add_trading_pair_does_not_raise(self):
        """Test MockedExchangeServer can add a trading pair with this plugin."""
        server = MockedExchangeServer(self.plugin, "127.0.0.1", 0)
        server.add_trading_pair(self.trading_pair, self.interval, 50000.0)
        assert self.trading_pair in server.candles

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        candles_route = "/api/v3/brokerage/market/products/{product_id}/candles"
        assert routes[candles_route] == ("GET", "handle_klines")
        assert self.plugin.ws_routes == {"/": "handle_websocket"}
        assert callable(self.plugin.handle_klines)
        assert callable(self.plugin.handle_websocket)
        assert "/api/v3/time" in routes
        assert "/api/v3/brokerage/products" in routes

    def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with query parameters
        from aiohttp.test_utils import make_mocked_request

        request = make_mocked_request(
            "GET",
            "/api/v3/brokerage/market/products/BTC-USD/candles"
            "?granularity=FIVE_MINUTE&start=1672531200&end=1672534800&limit=100",
            headers={},
            match_info={"product_id": "BTC-USD"},
        )

        # Parse parameters
        params = self.plugin.parse_rest_candles_params(request)

        # Seconds in the request become the milliseconds the server compares
        assert params["symbol"] == "BTC-USD"
        assert params["interval"] == "5m"
        assert params["limit"] == 100
        assert params["start_time"] == 1672531200 * 1000
        assert params["end_time"] == 1672534800 * 1000

    def test_parse_rest_candles_params_caps_limit_and_rejects_seconds_granularity(self):
        """Limit is capped at 350 and a seconds-valued granularity is invalid."""
        from aiohttp.test_utils import make_mocked_request

        base = "/api/v3/brokerage/market/products/BTC-USD/candles"
        capped = self.plugin.parse_rest_candles_params(
            make_mocked_request("GET", f"{base}?granularity=ONE_MINUTE&limit=1000")
        )
        assert capped["limit"] == 350

        invalid = self.plugin.parse_rest_candles_params(
            make_mocked_request("GET", f"{base}?granularity=60")
        )
        assert invalid["valid"] is False

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
        formatted = self.plugin.format_rest_candles(candles, self.trading_pair, self.interval, 0)

        # Check formatted data
        assert isinstance(formatted, dict)
        assert "candles" in formatted
        assert len(formatted["candles"]) == 1

        # Check first candle: `start` is a UNIX-seconds string
        candle_data = formatted["candles"][0]
        assert candle_data["start"] == "1620000000"
        assert candle_data["open"] == str(candles[0].open)
        assert candle_data["high"] == str(candles[0].high)
        assert candle_data["low"] == str(candles[0].low)
        assert candle_data["close"] == str(candles[0].close)
        assert candle_data["volume"] == str(candles[0].volume)

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
        assert "client_id" in message
        assert "timestamp" in message
        assert "sequence_num" in message
        assert "events" in message
        assert len(message["events"]) == 1
        assert message["events"][0]["type"] == "update"

        # Check candle data
        candle_data = message["events"][0]["candles"][0]
        assert candle_data["start"] == "1620000000"
        assert candle_data["product_id"] == "BTC-USD"
        assert candle_data["open"] == str(candle.open)
        assert candle_data["high"] == str(candle.high)
        assert candle_data["low"] == str(candle.low)
        assert candle_data["close"] == str(candle.close)
        assert candle_data["volume"] == str(candle.volume)

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message
        message = {
            "type": "subscribe",
            "product_ids": ["BTC-USD", "ETH-USD"],
            "channel": "candles",
        }

        # Parse subscription: the candles channel is fixed at 5 minutes
        subscriptions = self.plugin.parse_ws_subscription(message)

        assert subscriptions == [("BTC-USD", "5m"), ("ETH-USD", "5m")]

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        # Create subscription message
        message = {
            "type": "subscribe",
            "product_ids": ["BTC-USD"],
            "channel": "candles",
        }

        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USD", "5m")])

        # Check response format
        assert response["channel"] == "subscriptions"
        assert response["events"] == [{"subscriptions": {"candles": ["BTC-USD"]}}]

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USD", "5m")

        # Check key format; a pair registered without separator maps to the same key
        assert key == "candles_BTC-USD_5m"
        assert self.plugin.create_ws_subscription_key("BTCUSD", "5m") == key

    async def test_handle_products(self):
        """Test handling products endpoint."""
        from unittest.mock import AsyncMock, MagicMock

        # Create mocks
        mock_server = MagicMock()
        mock_server._simulate_network_conditions = AsyncMock()
        mock_server._check_rate_limit = MagicMock(return_value=True)
        mock_server.trading_pairs = {"BTC-USD": 50000.0, "ETH-USD": 3000.0}

        # Create mock request
        mock_request = MagicMock()
        mock_request.remote = "127.0.0.1"

        # Call the method
        response = await self.plugin.handle_products(mock_server, mock_request)

        # Check if server methods were called
        mock_server._simulate_network_conditions.assert_called_once()
        mock_server._check_rate_limit.assert_called_once_with("127.0.0.1", "rest")

        # Response should not be None
        assert response is not None

    async def test_handle_time(self):
        """Test handling time endpoint."""
        from unittest.mock import AsyncMock, MagicMock

        # Create mocks
        mock_server = MagicMock()
        mock_server._simulate_network_conditions = AsyncMock()
        mock_server._check_rate_limit = MagicMock(return_value=True)
        mock_server._time = MagicMock(return_value=1620000000)

        # Create mock request
        mock_request = MagicMock()
        mock_request.remote = "127.0.0.1"

        # Call the method
        response = await self.plugin.handle_time(mock_server, mock_request)

        # Check if server methods were called
        mock_server._simulate_network_conditions.assert_called_once()
        mock_server._check_rate_limit.assert_called_once_with("127.0.0.1", "rest")

        # Response should not be None
        assert response is not None
