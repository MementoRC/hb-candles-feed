"""
Unit tests for the AscendExBaseAdapter class.
"""

from unittest.mock import MagicMock

import pytest

from candles_feed.adapters.ascend_ex.base_adapter import AscendExBaseAdapter
from candles_feed.adapters.ascend_ex.constants import (
    INTERVALS,
    INTERVAL_TO_EXCHANGE_FORMAT,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData


class ConcreteAscendExAdapter(AscendExBaseAdapter):
    """Concrete implementation of AscendExBaseAdapter for testing."""

    @staticmethod
    def _get_rest_url() -> str:
        return "https://test.ascendex.com/api/pro/v1/barhist"

    @staticmethod
    def _get_ws_url() -> str:
        return "wss://test.ascendex.com:443/api/pro/v1/websocket-for-hummingbot-liq-mining/stream"


class TestAscendExBaseAdapter:
    """Test suite for the AscendExBaseAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = ConcreteAscendExAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # Test standard case
        assert self.adapter.get_trading_pair_format("BTC-USDT") == "BTC/USDT"

        # Test with multiple hyphens
        assert self.adapter.get_trading_pair_format("BTC-USDT-PERP") == "BTC/USDT/PERP"

        # Test with lowercase
        assert self.adapter.get_trading_pair_format("btc-usdt") == "btc/usdt"

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter._get_rest_params(self.trading_pair, self.interval)

        assert params["symbol"] == "BTC/USDT"
        assert params["interval"] == INTERVAL_TO_EXCHANGE_FORMAT[self.interval]
        assert params["n"] == MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST
        assert "to" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        end_time = 1622592000  # 2021-06-02 00:00:00 UTC
        limit = 500

        params = self.adapter._get_rest_params(
            self.trading_pair, self.interval, end_time=end_time, limit=limit
        )

        assert params["symbol"] == "BTC/USDT"
        assert params["interval"] == INTERVAL_TO_EXCHANGE_FORMAT[self.interval]
        assert params["n"] == limit
        assert params["to"] == end_time * 1000  # Should be in milliseconds

    def test_parse_rest_response(self):
        """Test parsing REST API response."""
        # Sample AscendEx REST response
        rest_response = {
            "status": "ok",
            "data": [
                {
                    "data": {
                        "ts": 1672531200000,  # 2023-01-01 00:00:00 UTC in milliseconds
                        "o": "50000.0",
                        "h": "51000.0",
                        "l": "49000.0",
                        "c": "50500.0",
                        "v": "5000000.0"
                    }
                },
                {
                    "data": {
                        "ts": 1672531260000,  # 2023-01-01 00:01:00 UTC in milliseconds
                        "o": "50500.0",
                        "h": "52000.0",
                        "l": "50000.0",
                        "c": "51500.0",
                        "v": "7500000.0"
                    }
                }
            ]
        }

        candles = self.adapter._parse_rest_response(rest_response)

        # Verify response parsing
        assert len(candles) == 2

        # Check first candle
        assert candles[0].timestamp == 1672531200  # 2023-01-01 00:00:00 UTC in seconds
        assert candles[0].open == 50000.0
        assert candles[0].high == 51000.0
        assert candles[0].low == 49000.0
        assert candles[0].close == 50500.0
        assert candles[0].volume == 0.0  # No volume data available in AscendEx
        assert candles[0].quote_asset_volume == 5000000.0
        assert candles[0].n_trades == 0  # No trades data available in AscendEx
        assert candles[0].taker_buy_base_volume == 0.0  # No taker data available in AscendEx
        assert candles[0].taker_buy_quote_volume == 0.0  # No taker data available in AscendEx

        # Check second candle
        assert candles[1].timestamp == 1672531260  # 2023-01-01 00:01:00 UTC in seconds
        assert candles[1].open == 50500.0
        assert candles[1].high == 52000.0
        assert candles[1].low == 50000.0
        assert candles[1].close == 51500.0
        assert candles[1].volume == 0.0  # No volume data available in AscendEx
        assert candles[1].quote_asset_volume == 7500000.0
        assert candles[1].n_trades == 0  # No trades data available in AscendEx
        assert candles[1].taker_buy_base_volume == 0.0  # No taker data available in AscendEx
        assert candles[1].taker_buy_quote_volume == 0.0  # No taker data available in AscendEx

    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["op"] == "sub"
        assert payload["ch"] == f"bar:{INTERVAL_TO_EXCHANGE_FORMAT[self.interval]}:BTC/USDT"

    def test_parse_ws_message_valid(self):
        """Test parsing valid WebSocket message."""
        # Sample AscendEx WebSocket message
        ws_message = {
            "m": "bar",
            "data": {
                "ts": 1672531200000,  # 2023-01-01 00:00:00 UTC in milliseconds
                "o": "50000.0",
                "h": "51000.0",
                "l": "49000.0",
                "c": "50500.0",
                "v": "5000000.0"
            }
        }

        candles = self.adapter.parse_ws_message(ws_message)

        # Verify message parsing
        assert candles is not None
        assert len(candles) == 1

        candle = candles[0]
        assert candle.timestamp == 1672531200  # 2023-01-01 00:00:00 UTC in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 0.0  # No volume data available in AscendEx
        assert candle.quote_asset_volume == 5000000.0
        assert candle.n_trades == 0  # No trades data available in AscendEx
        assert candle.taker_buy_base_volume == 0.0  # No taker data available in AscendEx
        assert candle.taker_buy_quote_volume == 0.0  # No taker data available in AscendEx

    def test_parse_ws_message_ping(self):
        """Test parsing ping WebSocket message."""
        # Sample AscendEx ping message
        ws_message = {
            "m": "ping",
            "data": {
                "ts": 1672531200000  # 2023-01-01 00:00:00 UTC in milliseconds
            }
        }

        candles = self.adapter.parse_ws_message(ws_message)
        # Ping messages should be ignored, returning None
        assert candles is None

    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"m": "trade", "data": "some_data"}
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
        
    def test_get_ws_url_calls_implementation(self):
        """Test that get_ws_url calls the _get_ws_url implementation."""
        # Verify that the public get_ws_url method correctly calls the private implementation
        assert self.adapter.get_ws_url() == "wss://test.ascendex.com:443/api/pro/v1/websocket-for-hummingbot-liq-mining/stream"
        assert self.adapter.get_ws_url() == ConcreteAscendExAdapter._get_ws_url()

    def test_get_ws_supported_intervals(self):
        """Test getting WebSocket supported intervals."""
        ws_intervals = self.adapter.get_ws_supported_intervals()

        # Verify WS intervals match the expected values
        assert ws_intervals == WS_INTERVALS
        assert "1m" in ws_intervals
        assert "1h" in ws_intervals