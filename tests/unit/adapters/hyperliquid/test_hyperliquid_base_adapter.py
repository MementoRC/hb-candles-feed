"""
Tests for the HyperliquidBaseAdapter using the base adapter test class.
"""

import pytest
from unittest import mock
from datetime import datetime, timezone

from candles_feed.adapters.hyperliquid.base_adapter import HyperliquidBaseAdapter
from candles_feed.adapters.hyperliquid.constants import (
    INTERVALS,
    INTERVAL_TO_EXCHANGE_FORMAT,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    CHANNEL_NAME,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class ConcreteHyperliquidAdapter(HyperliquidBaseAdapter):
    """Concrete implementation of HyperliquidBaseAdapter for testing."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles."""
        return SPOT_REST_URL

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL."""
        return SPOT_WSS_URL


class TestHyperliquidBaseAdapter(BaseAdapterTest):
    """Test suite for the HyperliquidBaseAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return ConcreteHyperliquidAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        base, _ = trading_pair.split("-", 1)
        return base

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return SPOT_REST_URL

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return SPOT_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "type": "candles",
            "coin": self.get_expected_trading_pair_format(trading_pair),
            "resolution": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "type": "candles",
            "coin": self.get_expected_trading_pair_format(trading_pair),
            "resolution": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
            "startTime": start_time,  # Hyperliquid uses seconds
            "endTime": end_time,      # Hyperliquid uses seconds
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "method": "subscribe",
            "channel": CHANNEL_NAME,
            "coin": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        
        return [
            [base_time, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", "5000000.0"],
            [base_time + 60, "50500.0", "52000.0", "50000.0", "51500.0", "150.0", "7500000.0"],
        ]

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        
        return {
            "channel": CHANNEL_NAME,
            "data": [base_time, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", "5000000.0"],
        }
        
    # Additional test cases specific to HyperliquidBaseAdapter
    
    def test_timestamp_in_seconds(self, adapter):
        """Test that timestamps are correctly handled in seconds."""
        assert adapter.TIMESTAMP_UNIT == "seconds"
        
        # Test timestamp conversion methods
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC
        
        # To exchange should remain in seconds
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_seconds
        
        # Ensure timestamp is in seconds regardless of input
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds) == timestamp_seconds
        assert adapter.ensure_timestamp_in_seconds(str(timestamp_seconds)) == timestamp_seconds
        
    def test_trading_pair_format_special_cases(self, adapter):
        """Test trading pair format conversion special cases."""
        # Test standard case - Hyperliquid only uses the base asset
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC"
        
        # Test with multiple hyphens
        assert adapter.get_trading_pair_format("ETH-BTC-PERP") == "ETH"
        
        # Test lowercase
        assert adapter.get_trading_pair_format("sol-usdt") == "sol"
        
    def test_parse_rest_response_field_mapping(self, adapter):
        """Test correct mapping of REST response fields."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        candle_data = [timestamp, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", "5000000.0"]
        
        # Parse a mocked rest response with a single candle
        candles = adapter._parse_rest_response([candle_data])
        
        assert len(candles) == 1
        candle = candles[0]
        
        # Verify field mapping
        assert candle.timestamp == timestamp
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        assert candle.n_trades == 0
        assert candle.taker_buy_base_volume == 0.0
        assert candle.taker_buy_quote_volume == 0.0
        
    def test_parse_ws_message_field_mapping(self, adapter):
        """Test correct mapping of WebSocket message fields."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        candle_data = [timestamp, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", "5000000.0"]
        
        # Parse a mocked WebSocket message
        message = {
            "channel": CHANNEL_NAME,
            "data": candle_data
        }
        
        candles = adapter.parse_ws_message(message)
        
        assert len(candles) == 1
        candle = candles[0]
        
        # Verify field mapping
        assert candle.timestamp == timestamp
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        
    def test_parse_ws_message_validation(self, adapter):
        """Test WebSocket message validation."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        
        # Test with invalid channel
        invalid_channel = {
            "channel": "trades",
            "data": [timestamp, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", "5000000.0"]
        }
        assert adapter.parse_ws_message(invalid_channel) is None
        
        # Test with missing data
        missing_data = {
            "channel": CHANNEL_NAME,
        }
        assert adapter.parse_ws_message(missing_data) is None
        
        # Test with too few data elements
        short_data = {
            "channel": CHANNEL_NAME,
            "data": [timestamp, "50000.0", "51000.0"],  # Missing fields
        }
        assert adapter.parse_ws_message(short_data) is None
        
    def test_get_intervals(self, adapter):
        """Test interval handling."""
        # Test that the adapter returns the correct interval mappings
        assert adapter.get_supported_intervals() == INTERVALS
        
        # WebSocket supported intervals should match WS_INTERVALS constant
        ws_intervals = adapter.get_ws_supported_intervals()
        
        # All intervals should be supported
        for interval in INTERVALS:
            assert interval in ws_intervals