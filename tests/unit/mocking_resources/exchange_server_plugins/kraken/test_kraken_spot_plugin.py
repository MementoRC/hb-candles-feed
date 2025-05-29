"""
Unit tests for the KrakenSpotPlugin class.
"""

import pytest

from candles_feed.adapters.kraken.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    SPOT_CANDLES_ENDPOINT,
    TIME_ENDPOINT,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.kraken.spot_plugin import (
    KrakenSpotPlugin,
)


class TestKrakenSpotPlugin:
    """Test suite for the KrakenSpotPlugin."""

    def setup_method(self):
        """Set up the test."""
        self.plugin = KrakenSpotPlugin()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_initialization(self):
        """Test plugin initialization."""
        assert self.plugin.exchange_type == ExchangeType.KRAKEN_SPOT
        assert self.plugin.rest_url.startswith("https://")
        assert self.plugin.wss_url.startswith("wss://")
        assert "/ws" in self.plugin.ws_routes

    def test_rest_routes(self):
        """Test REST API routes."""
        routes = self.plugin.rest_routes
        assert SPOT_CANDLES_ENDPOINT in routes
        assert routes[SPOT_CANDLES_ENDPOINT][0] == "GET"
        assert routes[SPOT_CANDLES_ENDPOINT][1] == "handle_klines"
        assert TIME_ENDPOINT in routes

    @pytest.mark.asyncio
    async def test_parse_rest_candles_params(self):
        """Test parsing REST API parameters."""
        # Create a mock request with query parameters
        from aiohttp.test_utils import make_mocked_request

        request = make_mocked_request(
            "GET",
            f"{SPOT_CANDLES_ENDPOINT}?pair=XBT/USD&interval=1&since=1620000000",
            headers={},
        )

        # Parse parameters
        params = self.plugin.parse_rest_candles_params(request)

        # Check parsed parameters
        assert params["symbol"] == "BTC-USDT"  # XBT/USD -> BTC-USDT
        assert params["interval"] == "1m"  # 1 -> 1m
        assert params["limit"] == 720  # Kraken's default
        assert params["start_time"] == 1620000000

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

        # Check formatted data structure
        assert isinstance(formatted, dict)
        assert "error" in formatted
        assert "result" in formatted
        assert len(formatted["error"]) == 0  # No errors

        kraken_pair = "XBT/USD"
        assert kraken_pair in formatted["result"]

        # Check the candles array
        kraken_candles = formatted["result"][kraken_pair]
        assert len(kraken_candles) == 1

        # Check candle fields
        candle_data = kraken_candles[0]
        assert candle_data[0] == int(candles[0].timestamp)  # Time in seconds
        assert candle_data[1] == str(candles[0].open)       # Open
        assert candle_data[2] == str(candles[0].high)       # High
        assert candle_data[3] == str(candles[0].low)        # Low
        assert candle_data[4] == str(candles[0].close)      # Close
        assert float(candle_data[5]) < float(candles[0].close)  # VWAP should be slightly less than close
        assert candle_data[6] == str(candles[0].volume)     # Volume
        assert isinstance(candle_data[7], int)              # Count

        # Check last timestamp
        assert formatted["result"]["last"] == int(candles[0].timestamp)

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

        # Check message format - Kraken WS messages are arrays, not objects
        assert isinstance(message, list)
        assert len(message) == 4

        # Check channel ID (placeholder)
        assert message[0] == 0

        # Check candle data
        candle_data = message[1]

        # Check timestamp format - Kraken uses seconds.microseconds format
        timestamp_str = candle_data[0]
        assert "." in timestamp_str, "Timestamp should include decimal for microseconds"
        timestamp_parts = timestamp_str.split(".")
        assert len(timestamp_parts) == 2, "Timestamp should have seconds and microseconds parts"
        assert timestamp_parts[0] == str(int(candle.timestamp)), "Seconds part should match timestamp"
        assert len(timestamp_parts[1]) > 0, "Microseconds part should not be empty"

        # Check end time format
        end_time_str = candle_data[1]
        assert "." in end_time_str, "End time should include decimal for microseconds"

        # Check price values with 5 decimal places
        assert float(candle_data[2]) == candle.open  # Open
        assert len(candle_data[2].split(".")[-1]) == 5, "Open price should have 5 decimal places"
        assert float(candle_data[3]) == candle.high  # High
        assert len(candle_data[3].split(".")[-1]) == 5, "High price should have 5 decimal places"
        assert float(candle_data[4]) == candle.low   # Low
        assert len(candle_data[4].split(".")[-1]) == 5, "Low price should have 5 decimal places"
        assert float(candle_data[5]) == candle.close # Close
        assert len(candle_data[5].split(".")[-1]) == 5, "Close price should have 5 decimal places"

        # Check VWAP (approximated)
        assert float(candle_data[6]) < candle.close

        # Check volume with 8 decimal places
        assert float(candle_data[7]) == candle.volume  # Volume
        assert len(candle_data[7].split(".")[-1]) == 8, "Volume should have 8 decimal places"

        # Check channel name with interval
        assert message[2] == f"ohlc-{INTERVAL_TO_EXCHANGE_FORMAT.get('1m', 1)}"

        # Check pair name
        assert message[3] in ["BTC/USDT", "XBT/USD"]  # Either format is acceptable

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        # Create subscription message in Kraken format
        message = {
            "name": "subscribe",
            "reqid": 1,
            "pair": ["XBT/USD"],
            "subscription": {
                "name": "ohlc",
                "interval": 1
            }
        }

        # Parse subscription
        subscriptions = self.plugin.parse_ws_subscription(message)

        # Check parsed subscriptions
        assert len(subscriptions) == 1
        # XBT/USD should be converted to BTC-USDT
        assert subscriptions[0][0] == "BTC-USDT"
        # Interval 1 should be converted to 1m
        assert subscriptions[0][1] == "1m"

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        # Create subscription message
        message = {
            "name": "subscribe",
            "reqid": 1,
            "pair": ["XBT/USD"],
            "subscription": {
                "name": "ohlc",
                "interval": 1
            }
        }

        # Create success response
        response = self.plugin.create_ws_subscription_success(message, [("BTC-USDT", "1m")])

        # Check response format
        assert isinstance(response, dict)
        assert "channelID" in response
        assert response["channelName"] == "ohlc-1"
        assert response["pair"] in ["BTC/USDT", "XBT/USD"]
        assert response["reqid"] == 1
        assert response["status"] == "subscribed"
        assert response["subscription"]["interval"] == 1
        assert response["subscription"]["name"] == "ohlc"

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        # Create subscription key
        key = self.plugin.create_ws_subscription_key("BTC-USDT", "1m")

        # Check key format - should contain ohlc-1 and the trading pair
        assert key.startswith("ohlc-1_")
        # Key should contain the trading pair in Kraken format
        assert "BTC/USDT" in key or "XBT/USD" in key

    def test_format_trading_pair(self):
        """Test formatting trading pair to Kraken format."""
        # Test regular pair
        formatted = self.plugin._format_trading_pair("BTC-USDT")
        assert formatted in ["BTC/USDT", "XBT/USD"]

        # Test another pair
        formatted = self.plugin._format_trading_pair("ETH-USD")
        assert formatted in ["ETH/USD", "XETH/ZUSD"]

    def test_reverse_format_trading_pair(self):
        """Test converting Kraken trading pair format back to standard."""
        # Test slash format
        standard = self.plugin._reverse_format_trading_pair("XBT/USD")
        assert standard == "BTC-USDT"

        # Test non-special pair
        standard = self.plugin._reverse_format_trading_pair("ETH/USD")
        assert standard in ["ETH-USD", "ETH-USDT"]
