"""
Unit tests for the KuCoinPerpetualAdapter class.
"""

import time
from unittest.mock import patch

import pytest

from candles_feed.adapters.kucoin.constants import (
    INTERVAL_TO_KUCOIN_PERP_FORMAT,
    INTERVALS,
    WS_INTERVALS,
)
from candles_feed.adapters.kucoin.constants import (
    PERP_CANDLES_ENDPOINT,
    PERP_REST_URL,
    PERP_WSS_URL,
)
from candles_feed.adapters.kucoin.kucoin_perpetual_adapter import KuCoinPerpetualAdapter
from candles_feed.core.candle_data import CandleData


class TestKuCoinPerpetualAdapter:
    """Test suite for the KuCoinPerpetualAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = KuCoinPerpetualAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # KuCoin doesn't change the format
        assert self.adapter.get_trading_pair_format("BTC-USDT") == "BTC-USDT"
        assert self.adapter.get_trading_pair_format("ETH-BTC") == "ETH-BTC"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert self.adapter.get_rest_url() == f"{PERP_REST_URL}{PERP_CANDLES_ENDPOINT}"

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert self.adapter.get_ws_url() == PERP_WSS_URL

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)

        assert params["symbol"] == self.trading_pair
        assert params["granularity"] == INTERVAL_TO_KUCOIN_PERP_FORMAT.get(
            self.interval, self.interval
        )
        assert "from" not in params
        assert "to" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        end_time = 1622592000  # 2021-06-02 00:00:00 UTC

        params = self.adapter.get_rest_params(
            self.trading_pair, self.interval, start_time=start_time, end_time=end_time
        )

        assert params["symbol"] == self.trading_pair
        assert params["granularity"] == INTERVAL_TO_KUCOIN_PERP_FORMAT.get(
            self.interval, self.interval
        )
        assert params["from"] == start_time * 1000  # Converted to milliseconds
        assert params["to"] == end_time * 1000  # Converted to milliseconds

    def test_parse_rest_response(self):
        """Test parsing REST API response."""
        # Create a sample perpetual response
        timestamp = 1672531200  # 2023-01-01 00:00:00 UTC
        response = {
            "code": "200000",
            "data": [
                [
                    timestamp,
                    50000.0,  # open
                    50500.0,  # close
                    51000.0,  # high
                    49000.0,  # low
                    100.0,  # volume
                    5000000.0,  # turnover
                ],
                [
                    timestamp + 60,
                    50500.0,  # open
                    51500.0,  # close
                    52000.0,  # high
                    50000.0,  # low
                    150.0,  # volume
                    7500000.0,  # turnover
                ],
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

    def test_parse_rest_response_empty(self):
        """Test parsing empty REST API response."""
        response = {"code": "200000", "data": []}
        candles = self.adapter.parse_rest_response(response)
        assert candles == []

    @patch("time.time")
    def test_get_ws_subscription_payload(self, mock_time):
        """Test WebSocket subscription payload generation."""
        mock_time.return_value = 1672531200.0
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        perp_interval = INTERVAL_TO_KUCOIN_PERP_FORMAT.get(self.interval, self.interval)
        assert payload["id"] == 1672531200000  # Fixed timestamp from mock
        assert payload["type"] == "subscribe"
        assert payload["topic"] == f"/contractMarket/candle:{self.trading_pair}_{perp_interval}"
        assert payload["privateChannel"] is False
        assert payload["response"] is True

    def test_parse_ws_message_valid(self):
        """Test parsing valid WebSocket message."""
        # Create a sample perpetual websocket message
        timestamp = 1672531200  # 2023-01-01 00:00:00 UTC
        message = {
            "type": "message",
            "topic": f"/contractMarket/candle:{self.trading_pair}_{INTERVAL_TO_KUCOIN_PERP_FORMAT.get(self.interval, self.interval)}",
            "subject": "candle.update",
            "data": {
                "symbol": self.trading_pair,
                "candles": [
                    str(timestamp),
                    "50000.0",  # open
                    "50500.0",  # close
                    "51000.0",  # high
                    "49000.0",  # low
                    "100.0",  # volume
                    "5000000.0",  # turnover
                ],
            },
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
        ws_message = {"type": "message", "topic": "/contractMarket/ticker"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = self.adapter.parse_ws_message(None)
        assert candles is None

        # Test with missing candles field
        ws_message = {
            "type": "message",
            "topic": f"/contractMarket/candle:{self.trading_pair}_1min",
            "data": {"symbol": self.trading_pair},
        }
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
        assert len(ws_intervals) == 1  # KuCoin only supports 1m in WebSocket
