"""
Unit tests for the MockedAdapter class.
"""

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.adapter.constants import (
    DEFAULT_CANDLES_LIMIT,
    REST_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.mocking_resources.adapter.mocked_adapter import MockedAdapter


class TestMockedAdapter:
    """Test suite for MockedAdapter."""

    def setup_method(self):
        """Set up the test."""
        self.adapter = MockedAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_intervals(self):
        """Test get_intervals method."""
        intervals = self.adapter.get_intervals()
        assert isinstance(intervals, dict)
        assert "1m" in intervals
        assert intervals["1m"] == 60  # 1 minute in seconds

    def test_get_supported_intervals(self):
        """Test get_supported_intervals method."""
        intervals = self.adapter.get_supported_intervals()
        assert isinstance(intervals, dict)
        assert "1m" in intervals
        assert intervals["1m"] == 60

    def test_get_ws_supported_intervals(self):
        """Test get_ws_supported_intervals method."""
        intervals = self.adapter.get_ws_supported_intervals()
        assert isinstance(intervals, list)
        assert "1m" in intervals

    def test_get_trading_pair_format(self):
        """Test get_trading_pair_format method."""
        formatted = self.adapter.get_trading_pair_format(self.trading_pair)
        assert formatted == self.trading_pair  # Should be unchanged for simple mock

    def test_get_rest_url(self):
        """Test get_rest_url method."""
        url = self.adapter.get_rest_url()
        assert url == f"{SPOT_REST_URL}{REST_CANDLES_ENDPOINT}"

    def test_get_ws_url(self):
        """Test get_ws_url method."""
        url = self.adapter.get_ws_url()
        assert url == SPOT_WSS_URL

    def test_get_rest_params(self):
        """Test get_rest_params method."""
        # Test with minimal parameters
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)
        assert params["symbol"] == self.trading_pair
        assert params["interval"] == self.interval
        assert params["limit"] == DEFAULT_CANDLES_LIMIT

        # Test with all parameters
        params = self.adapter.get_rest_params(
            self.trading_pair,
            self.interval,
            limit=100,
            start_time=1620000000000,
            end_time=1620100000000
        )
        assert params["symbol"] == self.trading_pair
        assert params["interval"] == self.interval
        assert params["limit"] == 100
        assert params["start_time"] == 1620000000000
        assert params["end_time"] == 1620100000000

    def test_parse_rest_response(self):
        """Test parse_rest_response method."""
        # Create a mock response
        response_data = {
            "status": "ok",
            "symbol": self.trading_pair,
            "interval": self.interval,
            "data": [
                {
                    "timestamp": 1620000000000,
                    "open": "50000.0",
                    "high": "51000.0",
                    "low": "49000.0",
                    "close": "50500.0",
                    "volume": "10.5",
                    "quote_volume": "525000.0"
                },
                {
                    "timestamp": 1620060000000,
                    "open": "50500.0",
                    "high": "52000.0",
                    "low": "50000.0",
                    "close": "51500.0",
                    "volume": "15.5",
                    "quote_volume": "775000.0"
                }
            ]
        }

        # Process the response
        candles = self.adapter.parse_rest_response(response_data, self.trading_pair, self.interval)

        # Check results
        assert len(candles) == 2
        assert isinstance(candles[0], CandleData)
        assert candles[0].timestamp_ms == 1620000000000
        assert candles[0].open == 50000.0
        assert candles[0].high == 51000.0
        assert candles[0].low == 49000.0
        assert candles[0].close == 50500.0
        assert candles[0].volume == 10.5
        assert candles[0].quote_asset_volume == 525000.0

    def test_get_ws_subscription_payload(self):
        """Test get_ws_subscription_payload method."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["type"] == "subscribe"
        assert isinstance(payload["subscriptions"], list)
        assert len(payload["subscriptions"]) == 1
        assert payload["subscriptions"][0]["symbol"] == self.trading_pair
        assert payload["subscriptions"][0]["interval"] == self.interval

    def test_parse_ws_message(self):
        """Test parse_ws_message method."""
        # Valid candle message
        valid_message = {
            "type": "candle_update",
            "symbol": self.trading_pair,
            "interval": self.interval,
            "data": {
                "timestamp": 1620000000000,
                "open": "50000.0",
                "high": "51000.0",
                "low": "49000.0",
                "close": "50500.0",
                "volume": "10.5",
                "quote_volume": "525000.0"
            }
        }

        # Process the message
        candle = self.adapter.parse_ws_message(valid_message)

        # Check result
        assert isinstance(candle[0], CandleData)
        assert candle[0].timestamp_ms == 1620000000000
        assert candle[0].open == 50000.0
        assert candle[0].high == 51000.0
        assert candle[0].low == 49000.0
        assert candle[0].close == 50500.0
        assert candle[0].volume == 10.5
        assert candle[0].quote_asset_volume == 525000.0
