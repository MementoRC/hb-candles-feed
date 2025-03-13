"""
Unit tests for the BinanceSpotPlugin class.
"""

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import BinanceSpotPlugin


class TestBinanceSpotPlugin:
    """Test suite for the BinanceSpotPlugin."""

    def setup_method(self):
        """Set up the test."""
        self.plugin = BinanceSpotPlugin()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.BINANCE_SPOT
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url.startswith("wss://")
        assert "/ws" in self.plugin.ws_routes

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        assert "/api/v3/klines" in routes
        assert routes["/api/v3/klines"][0] == "GET"
        assert routes["/api/v3/klines"][1] == "handle_klines"
        assert "/api/v3/exchangeInfo" in routes

    @pytest.mark.asyncio
    async def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with query parameters
        from aiohttp.test_utils import make_mocked_request
        
        request = make_mocked_request(
            "GET", 
            "/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=500&startTime=1620000000000&endTime=1620100000000",
            headers={},
        )
        
        # Parse parameters
        params = await self.plugin.parse_rest_candles_params(request)
        
        # Check parsed parameters
        assert params["symbol"] == "BTCUSDT"
        assert params["interval"] == "1m"
        assert params["limit"] == 500
        assert params["start_time"] == "1620000000000"
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
        assert isinstance(formatted, list)
        assert len(formatted) == 1
        assert formatted[0][0] == 1620000000000  # Open time
        assert formatted[0][1] == str(candles[0].open)  # Open
        assert formatted[0][2] == str(candles[0].high)  # High
        assert formatted[0][3] == str(candles[0].low)  # Low
        assert formatted[0][4] == str(candles[0].close)  # Close
        assert formatted[0][5] == str(candles[0].volume)  # Volume
        assert formatted[0][6] == 1620000000000 + (60 * 1000)  # Close time
        assert formatted[0][7] == str(candles[0].quote_asset_volume)  # Quote asset volume
        assert formatted[0][8] == 100  # Number of trades
        # In the implementation, these are calculated as 70% of the volume
        assert formatted[0][9] == str(candles[0].volume * 0.7)  # Taker buy base asset volume
        assert formatted[0][10] == str(candles[0].quote_asset_volume * 0.7)  # Taker buy quote asset volume
        assert formatted[0][11] == "0"  # Unused field

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
        message = self.plugin.format_ws_candle_message(candle, self.trading_pair, self.interval, is_final=True)
        
        # Check message format
        assert message["e"] == "kline"
        assert "E" in message
        assert message["s"] == "BTCUSDT"
        
        # Check kline data
        kline = message["k"]
        assert kline["t"] == 1620000000000  # Open time
        assert kline["T"] == 1620000000000 + (60 * 1000)  # Close time
        assert kline["s"] == "BTCUSDT"
        assert kline["i"] == "1m"
        assert kline["o"] == str(candle.open)
        assert kline["c"] == str(candle.close)
        assert kline["h"] == str(candle.high)
        assert kline["l"] == str(candle.low)
        assert kline["v"] == str(candle.volume)
        assert kline["n"] == 100
        assert kline["x"] is True  # Is final
        assert kline["q"] == str(candle.quote_asset_volume)
        # In the implementation, these are calculated as 70% of the volume
        assert kline["V"] == str(candle.volume * 0.7)
        assert kline["Q"] == str(candle.quote_asset_volume * 0.7)

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message
        message = {
            "method": "SUBSCRIBE",
            "params": ["btcusdt@kline_1m", "ethusdt@kline_5m"],
            "id": 12345
        }
        
        # Parse subscription
        subscriptions = self.plugin.parse_ws_subscription(message)
        
        # Check parsed subscriptions
        assert len(subscriptions) == 2
        assert subscriptions[0][0] == "BTC-USDT"
        assert subscriptions[0][1] == "1m"
        assert subscriptions[1][0] == "ETH-USDT"
        assert subscriptions[1][1] == "5m"

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        # Create subscription message
        message = {
            "method": "SUBSCRIBE",
            "params": ["btcusdt@kline_1m"],
            "id": 12345
        }
        
        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USDT", "1m")])
        
        # Check response format
        assert response["id"] == 12345
        assert response["result"] is None

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")
        
        # Check key format
        assert key == "btcusdt@kline_1m"

    @pytest.mark.asyncio
    async def test_handle_instruments(self):
        """Test handling instruments endpoint."""
        from unittest.mock import MagicMock, AsyncMock

        # Create mocks
        mock_server = MagicMock()
        mock_server._simulate_network_conditions = AsyncMock()
        mock_server._check_rate_limit = MagicMock(return_value=True)
        mock_server.trading_pairs = {"BTC-USDT": 50000.0, "ETH-USDT": 3000.0}
        mock_server._time = MagicMock(return_value=1620000000)
        
        # Instead of using make_mocked_request, create a MagicMock for the request
        mock_request = MagicMock()
        mock_request.query = {"instType": "SPOT"}
        mock_request.remote = "127.0.0.1"
        
        # Call the method
        response = await self.plugin.handle_instruments(mock_server, mock_request)
        
        # Check if server methods were called
        mock_server._simulate_network_conditions.assert_called_once()
        mock_server._check_rate_limit.assert_called_once_with("127.0.0.1", "rest")
        
        # Response should not be None
        assert response is not None