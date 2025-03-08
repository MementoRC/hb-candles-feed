"""
Unit tests for the HyperliquidSpotAdapter class.
"""

from unittest.mock import MagicMock

import pytest

from candles_feed.adapters.hyperliquid.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    SPOT_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.adapters.hyperliquid.spot_adapter import HyperliquidSpotAdapter
from candles_feed.core.candle_data import CandleData


class TestHyperliquidSpotAdapter:
    """Test suite for the HyperliquidSpotAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = HyperliquidSpotAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # Test standard case - HyperLiquid only uses the base asset
        assert HyperliquidSpotAdapter.get_trading_pair_format("BTC-USDT") == "BTC"

        # Test with multiple hyphens
        assert HyperliquidSpotAdapter.get_trading_pair_format("ETH-BTC-PERP") == "ETH"

    def test_get_rest_url(self):
        """Test REST API URL retrieval."""
        assert HyperliquidSpotAdapter.get_rest_url() == REST_URL

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert HyperliquidSpotAdapter.get_ws_url() == SPOT_WSS_URL

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)

        assert params["type"] == "candles"
        assert params["coin"] == "BTC"  # Only base asset
        assert params["resolution"] == INTERVAL_TO_EXCHANGE_FORMAT.get(
            self.interval, self.interval
        )
        assert params["limit"] == MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST
        assert "startTime" not in params
        assert "endTime" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        end_time = 1622592000  # 2021-06-02 00:00:00 UTC
        limit = 200

        params = self.adapter.get_rest_params(
            self.trading_pair, self.interval, start_time=start_time, end_time=end_time, limit=limit
        )

        assert params["type"] == "candles"
        assert params["coin"] == "BTC"  # Only base asset
        assert params["resolution"] == INTERVAL_TO_EXCHANGE_FORMAT.get(
            self.interval, self.interval
        )
        assert params["limit"] == limit
        assert params["startTime"] == start_time
        assert params["endTime"] == end_time

    def test_parse_rest_response(self, candlestick_response_hyperliquid):
        """Test parsing REST API response."""
        candles = self.adapter.parse_rest_response(candlestick_response_hyperliquid)

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

    def test_parse_rest_response_none(self):
        """Test parsing None REST API response."""
        candles = self.adapter.parse_rest_response(None)
        assert candles == []

    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["method"] == "subscribe"
        assert payload["channel"] == "candles"
        assert payload["coin"] == "BTC"
        assert payload["interval"] == INTERVAL_TO_EXCHANGE_FORMAT.get(
            self.interval, self.interval
        )

    def test_parse_ws_message_valid(self, websocket_message_hyperliquid):
        """Test parsing valid WebSocket message."""
        candles = self.adapter.parse_ws_message(websocket_message_hyperliquid)

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
        ws_message = {"channel": "trades", "data": "some_data"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = self.adapter.parse_ws_message(None)
        assert candles is None

    def test_get_supported_intervals(self):
        """Test getting supported intervals."""
        intervals = self.adapter.get_supported_intervals()

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
        ws_intervals = self.adapter.get_ws_supported_intervals()

        # Verify WS intervals match the expected values
        assert ws_intervals == WS_INTERVALS
        assert "1m" in ws_intervals
        assert "1h" in ws_intervals
