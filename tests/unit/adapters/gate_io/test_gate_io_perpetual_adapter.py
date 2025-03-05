"""
Unit tests for the GateIoPerpetualAdapter class.
"""

import pytest

from candles_feed.adapters.gate_io.constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    PERP_CANDLES_ENDPOINT,
    PERP_CHANNEL_NAME,
    PERP_REST_URL,
    PERP_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.adapters.gate_io.gate_io_perpetual_adapter import GateIoPerpetualAdapter
from candles_feed.core.candle_data import CandleData


class TestGateIoPerpetualAdapter:
    """Test suite for the GateIoPerpetualAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = GateIoPerpetualAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # Test standard case
        assert self.adapter.get_trading_pair_format("BTC-USDT") == "BTC_USDT"

        # Test with multiple hyphens
        assert self.adapter.get_trading_pair_format("BTC-USDT-PERP") == "BTC_USDT_PERP"

        # Test with lowercase
        assert self.adapter.get_trading_pair_format("btc-usdt") == "btc_usdt"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert self.adapter.get_rest_url() == PERP_REST_URL

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert self.adapter.get_ws_url() == PERP_WSS_URL

    def test_get_channel_name(self):
        """Test channel name retrieval."""
        assert self.adapter.get_channel_name() == PERP_CHANNEL_NAME

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)

        assert params["currency_pair"] == "BTC_USDT"
        assert params["interval"] == self.interval
        assert params["limit"] == MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST
        assert "from" not in params
        assert "to" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        end_time = 1622592000  # 2021-06-02 00:00:00 UTC
        limit = 500

        params = self.adapter.get_rest_params(
            self.trading_pair, self.interval, start_time=start_time, end_time=end_time, limit=limit
        )

        assert params["currency_pair"] == "BTC_USDT"
        assert params["interval"] == self.interval
        assert params["limit"] == limit
        assert params["from"] == start_time
        assert params["to"] == end_time

    def test_parse_rest_response(self, candlestick_response_gate_io):
        """Test parsing REST API response."""
        candles = self.adapter.parse_rest_response(candlestick_response_gate_io)

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
        assert candles[0].n_trades == 0  # Gate.io doesn't provide trade count
        assert candles[0].taker_buy_base_volume == 0.0  # Gate.io doesn't provide taker data
        assert candles[0].taker_buy_quote_volume == 0.0  # Gate.io doesn't provide taker data

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
        assert len(payload["params"]) == 2
        assert payload["params"][0] == PERP_CHANNEL_NAME
        assert payload["params"][1]["currency_pair"] == "BTC_USDT"
        assert payload["params"][1]["interval"] == "1m"
        assert payload["id"] == 12345

    def test_parse_ws_message_valid(self, websocket_message_gate_io):
        """Test parsing valid WebSocket message."""
        # Modify the channel to match perpetual
        modified_message = websocket_message_gate_io.copy()
        modified_message["channel"] = PERP_CHANNEL_NAME

        candles = self.adapter.parse_ws_message(modified_message)

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
        assert candle.n_trades == 0  # Gate.io doesn't provide trade count
        assert candle.taker_buy_base_volume == 0.0  # Gate.io doesn't provide taker data
        assert candle.taker_buy_quote_volume == 0.0  # Gate.io doesn't provide taker data

    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"method": "ping", "params": []}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = self.adapter.parse_ws_message(None)
        assert candles is None

        # Test with wrong channel
        ws_message = {"method": "update", "channel": "spot.trades", "params": []}
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
