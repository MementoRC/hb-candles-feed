"""
Unit tests for the Binance Spot plugin in mocking_resources.
"""

import unittest
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from candles_feed.core.candle_data import CandleData
from mocking_resources.core import ExchangeType
from candles_feed.mocking_resources.exchanges.binance.spot_plugin import BinanceSpotPlugin


class TestBinanceSpotPlugin(unittest.IsolatedAsyncioTestCase):
    """Tests for the BinanceSpotPlugin class."""

    def setUp(self):
        """Set up test fixtures."""
        self.plugin = BinanceSpotPlugin()

        # Create a sample candle for testing
        self.candle = CandleData(
            timestamp_raw=1613677200,
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50200.0,
            volume=10.0,
            quote_asset_volume=500000.0,
            n_trades=100,
            taker_buy_base_volume=7.0,
            taker_buy_quote_volume=350000.0,
        )

    def test_init(self):
        """Test initialization of the plugin."""
        self.assertEqual(self.plugin.exchange_type, ExchangeType.BINANCE_SPOT)

    def test_rest_routes(self):
        """Test the rest_routes property."""
        routes = self.plugin.rest_routes
        self.assertIsInstance(routes, dict)
        self.assertIn("/api/v3/ping", routes)
        self.assertIn("/api/v3/time", routes)
        self.assertIn("/api/v3/klines", routes)
        self.assertIn("/api/v3/exchangeInfo", routes)

    def test_ws_routes(self):
        """Test the ws_routes property."""
        routes = self.plugin.ws_routes
        self.assertIsInstance(routes, dict)
        self.assertIn("/ws", routes)

    def test_format_rest_candles(self):
        """Test formatting REST candles response."""
        candles = [self.candle]

        result = self.plugin.format_rest_candles(candles, "BTCUSDT", "1m")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        candle_data = result[0]
        # Check array length
        self.assertEqual(len(candle_data), 12)

        # Check data types and formats
        self.assertEqual(candle_data[0], self.candle.timestamp_ms)  # Open time in ms
        self.assertEqual(candle_data[1], str(self.candle.open))
        self.assertEqual(candle_data[2], str(self.candle.high))
        self.assertEqual(candle_data[3], str(self.candle.low))
        self.assertEqual(candle_data[4], str(self.candle.close))
        self.assertEqual(candle_data[5], str(self.candle.volume))
        # Close time should be open time + interval in ms
        self.assertEqual(candle_data[6], self.candle.timestamp_ms + (60 * 1000))  # 1m interval
        self.assertEqual(candle_data[7], str(self.candle.quote_asset_volume))
        self.assertEqual(candle_data[8], self.candle.n_trades)
        self.assertEqual(candle_data[9], str(self.candle.taker_buy_base_volume))
        self.assertEqual(candle_data[10], str(self.candle.taker_buy_quote_volume))
        self.assertEqual(candle_data[11], "0")  # Unused field

    def test_format_ws_candle_message(self):
        """Test formatting WebSocket candle message."""
        result = self.plugin.format_ws_candle_message(self.candle, "BTCUSDT", "1m", is_final=True)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["e"], "kline")
        self.assertIsInstance(result["E"], int)  # Event time
        self.assertEqual(result["s"], "BTCUSDT")

        # Check kline data
        kline = result["k"]
        self.assertEqual(kline["t"], self.candle.timestamp_ms)
        self.assertEqual(kline["T"], self.candle.timestamp_ms + (60 * 1000))
        self.assertEqual(kline["s"], "BTCUSDT")
        self.assertEqual(kline["i"], "1m")
        self.assertEqual(kline["o"], str(self.candle.open))
        self.assertEqual(kline["c"], str(self.candle.close))
        self.assertEqual(kline["h"], str(self.candle.high))
        self.assertEqual(kline["l"], str(self.candle.low))
        self.assertEqual(kline["v"], str(self.candle.volume))
        self.assertEqual(kline["n"], self.candle.n_trades)
        self.assertEqual(kline["x"], True)  # Is final
        self.assertEqual(kline["q"], str(self.candle.quote_asset_volume))
        self.assertEqual(kline["V"], str(self.candle.taker_buy_base_volume))
        self.assertEqual(kline["Q"], str(self.candle.taker_buy_quote_volume))

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        message = {
            "method": "SUBSCRIBE",
            "params": ["btcusdt@kline_1m", "ethusdt@kline_5m"],
            "id": 1,
        }

        result = self.plugin.parse_ws_subscription(message)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("BTCUSDT", "1m"))
        self.assertEqual(result[1], ("ETHUSDT", "5m"))

    def test_parse_ws_subscription_invalid(self):
        """Test parsing invalid WebSocket subscription message."""
        # Arrange - wrong method
        message1 = {"method": "UNSUBSCRIBE", "params": ["btcusdt@kline_1m"], "id": 1}

        # Arrange - invalid channel format
        message2 = {"method": "SUBSCRIBE", "params": ["btcusdt@trades"], "id": 1}

        result1 = self.plugin.parse_ws_subscription(message1)
        result2 = self.plugin.parse_ws_subscription(message2)

        self.assertEqual(result1, [])
        self.assertEqual(result2, [])

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        message = {"method": "SUBSCRIBE", "params": ["btcusdt@kline_1m"], "id": 123}
        subscriptions = [("BTCUSDT", "1m")]

        result = self.plugin.create_ws_subscription_success(message, subscriptions)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["result"], None)
        self.assertEqual(result["id"], 123)

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        result = self.plugin.create_ws_subscription_key("BTCUSDT", "1m")

        self.assertEqual(result, "btcusdt@kline_1m")

    def test_parse_rest_candles_params(self):
        """Test parsing REST candles parameters."""
        mock_request = MagicMock()
        mock_request.query = {
            "symbol": "BTCUSDT",
            "interval": "1m",
            "startTime": "1613677200000",
            "endTime": "1613680800000",
            "limit": "500",
        }

        result = self.plugin.parse_rest_candles_params(mock_request)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["symbol"], "BTCUSDT")
        self.assertEqual(result["interval"], "1m")
        self.assertEqual(result["start_time"], "1613677200000")
        self.assertEqual(result["end_time"], "1613680800000")
        self.assertEqual(result["limit"], 500)

    @pytest.mark.asyncio
    @patch("time.time")
    async def test_handle_exchange_info(self, mock_time):
        """Test handling exchange info request."""
        mock_time.return_value = 1613677200

        mock_server = MagicMock()
        mock_server._simulate_network_conditions = AsyncMock()
        mock_server._check_rate_limit = MagicMock(return_value=True)
        mock_server.trading_pairs = {"BTCUSDT": 50000.0, "ETHUSDT": 3000.0}

        mock_request = MagicMock()
        mock_request.remote = "127.0.0.1"

        response = await self.plugin.handle_instruments(mock_server, mock_request)

        mock_server._simulate_network_conditions.assert_called_once()
        mock_server._check_rate_limit.assert_called_once_with("127.0.0.1", "rest")

        # Check response format
        self.assertEqual(response.status, 200)

        # Get response body (JSON)
        body = await response.json()

        self.assertEqual(body["serverTime"], 1613677200000)
        self.assertEqual(len(body["symbols"]), 2)

        # Check BTCUSDT symbol info
        btc_symbol = next(s for s in body["symbols"] if s["symbol"] == "BTCUSDT")
        self.assertEqual(btc_symbol["baseAsset"], "BTC")
        self.assertEqual(btc_symbol["quoteAsset"], "USDT")
        self.assertEqual(btc_symbol["status"], "TRADING")
        
        # Return None to fix deprecation warning
        return None


if __name__ == "__main__":
    unittest.main()
