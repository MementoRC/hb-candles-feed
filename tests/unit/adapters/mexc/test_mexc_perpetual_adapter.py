"""
Unit tests for the MEXCPerpetualAdapter class.
"""

import pytest

from candles_feed.adapters.mexc.constants import (
    INTERVAL_TO_PERPETUAL_FORMAT,
    INTERVALS,
    PERP_CANDLES_ENDPOINT,
    PERP_KLINE_TOPIC,
    PERP_REST_URL,
    PERP_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.adapters.mexc.perpetual_adapter import MEXCPerpetualAdapter
from candles_feed.core.candle_data import CandleData


class TestMEXCPerpetualAdapter:
    """Test suite for the MEXCPerpetualAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = MEXCPerpetualAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # Test standard case
        assert MEXCPerpetualAdapter.get_trading_pair_format("BTC-USDT") == "BTC_USDT"

        # Test with multiple hyphens
        assert MEXCPerpetualAdapter.get_trading_pair_format("BTC-USDT-PERP") == "BTC_USDT_PERP"

        # Test with lowercase
        assert MEXCPerpetualAdapter.get_trading_pair_format("btc-usdt") == "btc_usdt"

    def test_get_rest_url(self):
        """Test REST API URL retrieval."""
        assert MEXCPerpetualAdapter.get_rest_url() == PERP_REST_URL

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert MEXCPerpetualAdapter.get_ws_url() == PERP_WSS_URL

    def test_get_kline_topic(self):
        """Test kline topic retrieval."""
        assert self.adapter.get_kline_topic() == PERP_KLINE_TOPIC

    def test_get_interval_format(self):
        """Test getting interval format."""
        # Test standard intervals
        assert self.adapter.get_interval_format("1m") == "Min1"
        assert self.adapter.get_interval_format("1h") == "Min60"
        assert self.adapter.get_interval_format("1d") == "Day1"

        # Test fallback
        assert self.adapter.get_interval_format("unknown") == "unknown"

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)

        assert params["symbol"] == "BTC_USDT"
        assert params["interval"] == INTERVAL_TO_PERPETUAL_FORMAT.get(self.interval)
        assert "start" not in params
        assert "end" not in params
        assert "size" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        end_time = 1622592000  # 2021-06-02 00:00:00 UTC
        limit = 500

        params = self.adapter.get_rest_params(
            self.trading_pair, self.interval, start_time=start_time, end_time=end_time, limit=limit
        )

        assert params["symbol"] == "BTC_USDT"
        assert params["interval"] == INTERVAL_TO_PERPETUAL_FORMAT.get(self.interval)
        assert params["size"] == limit
        assert params["start"] == start_time  # Already in seconds
        assert params["end"] == end_time  # Already in seconds

    def test_parse_rest_response(self):
        """Test parsing REST API response."""
        # Create a sample contract REST response
        timestamp = 1672531200  # 2023-01-01 00:00:00 UTC
        response = {
            "success": True,
            "code": 0,
            "data": [
                {
                    "time": timestamp,
                    "open": "50000.0",
                    "close": "50500.0",
                    "high": "51000.0",
                    "low": "49000.0",
                    "vol": "100.0",
                    "amount": "5000000.0",
                },
                {
                    "time": timestamp + 60,
                    "open": "50500.0",
                    "close": "51500.0",
                    "high": "52000.0",
                    "low": "50000.0",
                    "vol": "150.0",
                    "amount": "7500000.0",
                },
            ],
        }

        candles = self.adapter.parse_rest_response(response)

        # Verify response parsing
        assert len(candles) == 2

        # Check first candle
        assert candles[0].timestamp == timestamp
        assert candles[0].open == 50000.0
        assert candles[0].high == 51000.0
        assert candles[0].low == 49000.0
        assert candles[0].close == 50500.0
        assert candles[0].volume == 100.0
        assert candles[0].quote_asset_volume == 5000000.0

        # Check second candle
        assert candles[1].timestamp == timestamp + 60
        assert candles[1].open == 50500.0
        assert candles[1].high == 52000.0
        assert candles[1].low == 50000.0
        assert candles[1].close == 51500.0
        assert candles[1].volume == 150.0
        assert candles[1].quote_asset_volume == 7500000.0

    def test_parse_rest_response_none(self):
        """Test parsing None REST API response."""
        candles = self.adapter.parse_rest_response(None)
        assert candles == []

    def test_parse_rest_response_invalid(self):
        """Test parsing invalid REST API response."""
        # Test with missing data field
        candles = self.adapter.parse_rest_response({"success": True})
        assert candles == []

        # Test with non-list data field
        candles = self.adapter.parse_rest_response({"success": True, "data": "not a list"})
        assert candles == []

    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["method"] == "sub"
        mexc_interval = INTERVAL_TO_PERPETUAL_FORMAT.get(self.interval, self.interval)
        expected_topic = f"{PERP_KLINE_TOPIC}{mexc_interval}_btcusdt"
        assert payload["params"][0] == expected_topic

    def test_parse_ws_message_valid(self):
        """Test parsing valid WebSocket message."""
        # Create a sample contract WebSocket message
        timestamp = 1672531200  # 2023-01-01 00:00:00 UTC
        message = {
            "channel": "push.kline",
            "data": {
                "a": "5000000.0",  # amount (quote volume)
                "c": "50500.0",  # close
                "h": "51000.0",  # high
                "interval": "Min1",  # interval
                "l": "49000.0",  # low
                "o": "50000.0",  # open
                "q": "0",  # ignore
                "symbol": "BTC_USDT",  # symbol
                "t": timestamp,  # timestamp
                "v": "100.0",  # volume
            },
            "symbol": "BTC_USDT",
        }

        candles = self.adapter.parse_ws_message(message)

        # Verify message parsing
        assert candles is not None
        assert len(candles) == 1

        candle = candles[0]
        assert candle.timestamp == timestamp
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0

    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"channel": "push.ticker", "data": "some_data"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = self.adapter.parse_ws_message(None)
        assert candles is None

        # Test with missing data
        ws_message = {"channel": "push.kline"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

    def test_get_supported_intervals(self):
        """Test getting supported intervals."""
        intervals = MEXCPerpetualAdapter.get_supported_intervals()

        # Verify intervals match the expected values
        assert intervals == INTERVALS
        assert "1m" in intervals
        assert intervals["1m"] == 60
        assert "1h" in intervals
        assert intervals["1h"] == 3600
        assert "1d" in intervals
        assert intervals["1d"] == 86400

    def test_get_ws_supported_intervals(self):
        """Test getting WebSocket supported intervals."""
        ws_intervals = MEXCPerpetualAdapter.get_ws_supported_intervals()

        # Verify WS intervals match the expected values
        assert ws_intervals == WS_INTERVALS
        assert "1m" in ws_intervals
        assert "1h" in ws_intervals
