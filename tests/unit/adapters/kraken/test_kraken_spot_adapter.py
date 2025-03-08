"""
Unit tests for the KrakenSpotAdapter class.
"""

from unittest.mock import MagicMock

import pytest

from candles_feed.adapters.kraken.constants import (
    SPOT_CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_REST_URL,
    WS_INTERVALS,
    SPOT_WSS_URL,
)
from candles_feed.adapters.kraken.spot_adapter import KrakenSpotAdapter
from candles_feed.core.candle_data import CandleData


class TestKrakenSpotAdapter:
    """Test suite for the KrakenSpotAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = KrakenSpotAdapter()
        self.trading_pair = "BTC-USD"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # Test standard case
        assert KrakenSpotAdapter.get_trading_pair_format("BTC-USD") == "XXBTZUSD"

        # Test with other currencies
        assert KrakenSpotAdapter.get_trading_pair_format("ETH-USD") == "XETHZUSD"
        assert KrakenSpotAdapter.get_trading_pair_format("BTC-EUR") == "XXBTZEUR"

        # Test with USDT
        assert KrakenSpotAdapter.get_trading_pair_format("BTC-USDT") == "XXBTZUSD"

        # Test with non-prefixed pairs
        assert KrakenSpotAdapter.get_trading_pair_format("DOT-USD") == "DOTZUSD"
        assert KrakenSpotAdapter.get_trading_pair_format("XRP-USD") == "XXRPZUSD"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert KrakenSpotAdapter.get_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert KrakenSpotAdapter.get_ws_url() == SPOT_WSS_URL

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)

        assert params["pair"] == "XXBTZUSD"
        assert params["interval"] == INTERVAL_TO_EXCHANGE_FORMAT[self.interval]
        assert "since" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC

        params = self.adapter.get_rest_params(
            self.trading_pair,
            self.interval,
            start_time=start_time,
            limit=500,  # Note: Kraken ignores limit parameter
        )

        assert params["pair"] == "XXBTZUSD"
        assert params["interval"] == INTERVAL_TO_EXCHANGE_FORMAT[self.interval]
        assert params["since"] == start_time

    def test_parse_rest_response(self, candlestick_response_kraken):
        """Test parsing REST API response."""
        candles = self.adapter.parse_rest_response(candlestick_response_kraken)

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

    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["name"] == "subscribe"
        assert payload["reqid"] == 1
        assert payload["pair"] == ["XXBTZUSD"]
        assert payload["subscription"]["name"] == "ohlc"
        assert payload["subscription"]["interval"] == INTERVAL_TO_EXCHANGE_FORMAT[self.interval]

    def test_parse_ws_message_valid(self, websocket_message_kraken):
        """Test parsing valid WebSocket message."""
        candles = self.adapter.parse_ws_message(websocket_message_kraken)

        # Verify message parsing
        assert candles is not None
        assert len(candles) == 1

        candle = candles[0]
        assert abs(candle.timestamp - 1672531200) < 1.0  # Allow small floating point difference
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert abs(candle.quote_asset_volume - 5000000.0) < 0.1  # Allow small rounding difference

    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"type": "heartbeat"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = self.adapter.parse_ws_message(None)
        assert candles is None

        # Test with wrong format
        ws_message = [0, [1672531200], "trades", "XXBTZUSD"]
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
