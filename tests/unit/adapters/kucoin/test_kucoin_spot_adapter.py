"""
Unit tests for the KucoinSpotAdapter class.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from candles_feed.adapters.kucoin.constants import (
    INTERVALS,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.adapters.kucoin.spot_adapter import KucoinSpotAdapter
from candles_feed.core.candle_data import CandleData


class TestKuCoinSpotAdapter:
    """Test suite for the KucoinSpotAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = KucoinSpotAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # KuCoin doesn't change the format
        assert KucoinSpotAdapter.get_trading_pair_format("BTC-USDT") == "BTC-USDT"
        assert KucoinSpotAdapter.get_trading_pair_format("ETH-BTC") == "ETH-BTC"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert KucoinSpotAdapter.get_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert KucoinSpotAdapter.get_ws_url() == SPOT_WSS_URL

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)

        assert params["symbol"] == self.trading_pair
        assert params["type"] == self.interval
        assert "startAt" not in params
        assert "endAt" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        end_time = 1622592000  # 2021-06-02 00:00:00 UTC
        limit = 500

        params = self.adapter.get_rest_params(
            self.trading_pair, self.interval, start_time=start_time, end_time=end_time, limit=limit
        )

        assert params["symbol"] == self.trading_pair
        assert params["type"] == self.interval
        assert params["limit"] == limit
        assert params["startAt"] == start_time * 1000  # Convert to milliseconds
        assert params["endAt"] == end_time * 1000  # Convert to milliseconds

    def test_parse_rest_response(self, candlestick_response_kucoin):
        """Test parsing REST API response."""
        candles = self.adapter.parse_rest_response(candlestick_response_kucoin)

        # Verify response parsing
        assert len(candles) == 2

        # Check first candle
        assert candles[0].timestamp == 1672531200  # 2023-01-01 00:00:00 UTC in seconds
        assert candles[0].open == 50000.0
        assert candles[0].high == 51000.0
        assert candles[0].low == 49000.0
        assert candles[0].close == 50500.0
        assert candles[0].volume == 100.0
        assert candles[0].quote_asset_volume == 5000000.0

        # Check second candle
        assert candles[1].timestamp == 1672531260  # 2023-01-01 00:01:00 UTC in seconds
        assert candles[1].open == 50500.0
        assert candles[1].high == 52000.0
        assert candles[1].low == 50000.0
        assert candles[1].close == 51500.0
        assert candles[1].volume == 150.0
        assert candles[1].quote_asset_volume == 7500000.0

    @patch("time.time")
    def test_get_ws_subscription_payload(self, mock_time):
        """Test WebSocket subscription payload generation."""
        mock_time.return_value = 1672531200.0
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["id"] == 1672531200000  # Fixed timestamp from mock
        assert payload["type"] == "subscribe"
        assert payload["topic"] == f"/market/candles:{self.trading_pair}_{self.interval}"
        assert payload["privateChannel"] is False
        assert payload["response"] is True

    def test_parse_ws_message_valid(self, websocket_message_kucoin):
        """Test parsing valid WebSocket message."""
        candles = self.adapter.parse_ws_message(websocket_message_kucoin)

        # Verify message parsing
        assert candles is not None
        assert len(candles) == 1

        candle = candles[0]
        assert candle.timestamp == 1672531200  # 2023-01-01 00:00:00 UTC in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0

    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"type": "message", "topic": "/market/ticker"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = self.adapter.parse_ws_message(None)
        assert candles is None

        # Test with missing candles field
        ws_message = {
            "type": "message",
            "topic": f"/market/candles:{self.trading_pair}_{self.interval}",
            "data": {"symbol": self.trading_pair},
        }
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

    def test_get_supported_intervals(self):
        """Test getting supported intervals."""
        intervals = KucoinSpotAdapter.get_supported_intervals()

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
        ws_intervals = KucoinSpotAdapter.get_ws_supported_intervals()

        # Verify WS intervals match the expected values
        assert ws_intervals == WS_INTERVALS
        assert "1m" in ws_intervals
        assert len(ws_intervals) == 1  # KuCoin only supports 1m in WebSocket
