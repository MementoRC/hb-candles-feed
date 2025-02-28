"""
Unit tests for the CoinbaseAdvancedTradeAdapter class.
"""

from unittest.mock import MagicMock

import pytest

from candles_feed.adapters.coinbase_advanced_trade.coinbase_advanced_trade_adapter import (
    CoinbaseAdvancedTradeAdapter,
)
from candles_feed.adapters.coinbase_advanced_trade.constants import (
    BASE_REST_URL,
    INTERVALS,
    MAX_CANDLES_SIZE,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData


class TestCoinbaseAdvancedTradeAdapter:
    """Test suite for the CoinbaseAdvancedTradeAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = CoinbaseAdvancedTradeAdapter()
        self.trading_pair = "BTC-USD"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # Coinbase keeps the same format
        assert self.adapter.get_trading_pair_format("BTC-USD") == "BTC-USD"
        assert self.adapter.get_trading_pair_format("ETH-USDT") == "ETH-USDT"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert self.adapter.get_rest_url() == BASE_REST_URL

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert self.adapter.get_ws_url() == WSS_URL

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)

        assert params["granularity"] == INTERVALS[self.interval]
        assert "start" not in params
        assert "end" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        end_time = 1622592000    # 2021-06-02 00:00:00 UTC

        params = self.adapter.get_rest_params(
            self.trading_pair,
            self.interval,
            start_time=start_time,
            end_time=end_time
        )

        assert params["granularity"] == INTERVALS[self.interval]
        assert params["start"] == start_time
        assert params["end"] == end_time
        # Coinbase doesn't use a limit parameter

    def test_parse_rest_response(self, candlestick_response_coinbase):
        """Test parsing REST API response."""
        candles = self.adapter.parse_rest_response(candlestick_response_coinbase)

        # Verify response parsing
        assert len(candles) == 2

        # Coinbase uses ISO timestamps
        # Check first candle
        assert isinstance(candles[0].timestamp, int)
        assert candles[0].open == 50000.0
        assert candles[0].high == 51000.0
        assert candles[0].low == 49000.0
        assert candles[0].close == 50500.0
        assert candles[0].volume == 100.0

        # Check second candle
        assert isinstance(candles[1].timestamp, int)
        assert candles[1].open == 50500.0
        assert candles[1].high == 52000.0
        assert candles[1].low == 50000.0
        assert candles[1].close == 51500.0
        assert candles[1].volume == 150.0

    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["type"] == "subscribe"
        assert payload["product_ids"] == [self.trading_pair]
        assert payload["channel"] == "candles"
        assert payload["granularity"] == INTERVALS[self.interval]

    def test_parse_ws_message_valid(self, websocket_message_coinbase):
        """Test parsing valid WebSocket message."""
        candles = self.adapter.parse_ws_message(websocket_message_coinbase)

        # Verify message parsing
        assert candles is not None
        assert len(candles) == 1

        candle = candles[0]
        assert isinstance(candle.timestamp, int)
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0

    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"channel": "heartbeat", "data": "some_data"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = self.adapter.parse_ws_message(None)
        assert candles is None

        # Test with missing events
        ws_message = {"channel": "candles", "timestamp": "2023-01-01T00:00:00Z"}
        candles = self.adapter.parse_ws_message(ws_message)
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
        # Verify 6h and 1d are not supported in WebSocket
        assert "6h" not in ws_intervals
        assert "1d" not in ws_intervals
