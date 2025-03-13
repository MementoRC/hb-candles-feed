"""
Tests for the GateIoBaseAdapter using the base adapter test class.
"""

import pytest
from unittest import mock
from datetime import datetime, timezone

from candles_feed.adapters.gate_io.base_adapter import GateIoBaseAdapter
from candles_feed.adapters.gate_io.constants import (
    INTERVALS,
    INTERVAL_TO_EXCHANGE_FORMAT,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_CHANNEL_NAME,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class ConcreteGateIoAdapter(GateIoBaseAdapter):
    """Concrete implementation of GateIoBaseAdapter for testing."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles."""
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL."""
        return SPOT_WSS_URL

    def get_channel_name(self) -> str:
        """Get WebSocket channel name."""
        return SPOT_CHANNEL_NAME


class TestGateIoBaseAdapter(BaseAdapterTest):
    """Test suite for the GateIoBaseAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return ConcreteGateIoAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair.replace("-", "_")

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return SPOT_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "currency_pair": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "currency_pair": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
            "from": start_time,  # Gate.io uses seconds
            "to": end_time,      # Gate.io uses seconds
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "method": "subscribe",
            "params": [
                f"{SPOT_CHANNEL_NAME}",
                {
                    "currency_pair": self.get_expected_trading_pair_format(trading_pair),
                    "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
                },
            ],
            "id": 12345,
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        
        return [
            [
                str(base_time),      # timestamp
                "50000.0",           # open
                "50500.0",           # close
                "49000.0",           # low
                "51000.0",           # high
                "100.0",             # volume
                "5000000.0",         # quote currency volume
                "BTC_USDT",          # currency pair
            ],
            [
                str(base_time + 60), # timestamp
                "50500.0",           # open
                "51500.0",           # close
                "50000.0",           # low
                "52000.0",           # high
                "150.0",             # volume
                "7500000.0",         # quote currency volume
                "BTC_USDT",          # currency pair
            ],
        ]

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        
        return {
            "method": "update",
            "channel": SPOT_CHANNEL_NAME,
            "params": [
                {"currency_pair": "BTC_USDT", "interval": "1m", "status": "open"},
                [
                    str(base_time),  # timestamp
                    "50000.0",       # open
                    "50500.0",       # close
                    "49000.0",       # low
                    "51000.0",       # high
                    "100.0",         # volume
                    "5000000.0",     # quote currency volume
                    "BTC_USDT",      # currency pair
                ],
            ],
        }
        
    # Additional test cases specific to GateIoBaseAdapter
    
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
        
    def test_param_generation(self, adapter):
        """Test parameter generation for API requests."""
        # Test with minimal parameters
        params = adapter._get_rest_params("BTC-USDT", "1m")
        assert params["currency_pair"] == "BTC_USDT"
        assert params["interval"] == "1m"
        assert params["limit"] == MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST
        
        # Test with full parameters
        start_time = 1622505600
        end_time = 1622592000
        limit = 500
        params = adapter._get_rest_params(
            "ETH-USDT", "5m", start_time=start_time, end_time=end_time, limit=limit
        )
        assert params["currency_pair"] == "ETH_USDT"
        assert params["interval"] == "5m"
        assert params["limit"] == limit
        assert params["from"] == start_time
        assert params["to"] == end_time
        
    def test_candle_data_field_mapping(self, adapter):
        """Test mapping of raw API data to CandleData fields."""
        # Test parsing a single candle record
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        candle_data = [
            str(timestamp),  # timestamp
            "50000.0",       # open
            "50500.0",       # close
            "49000.0",       # low
            "51000.0",       # high
            "100.0",         # volume
            "5000000.0",     # quote currency volume
            "BTC_USDT",      # currency pair
        ]
        
        # Parse a mocked rest response with a single candle
        candles = adapter._parse_rest_response([candle_data])
        
        assert len(candles) == 1
        candle = candles[0]
        
        # Verify field mapping
        assert candle.timestamp == timestamp  # timestamp is in seconds
        assert candle.timestamp_ms == timestamp * 1000  # timestamp_ms is derived from timestamp
        assert candle.open == 50000.0
        assert candle.close == 50500.0
        assert candle.low == 49000.0
        assert candle.high == 51000.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        # Other fields should be initialized with default values
        assert candle.n_trades == 0
        assert candle.taker_buy_base_volume == 0.0
        assert candle.taker_buy_quote_volume == 0.0
        
    def test_get_intervals(self, adapter):
        """Test interval handling."""
        # Test that the adapter returns the correct interval mappings
        assert adapter.get_supported_intervals() == INTERVALS
        
        # WebSocket supported intervals should match WS_INTERVALS constant
        ws_intervals = adapter.get_ws_supported_intervals()
        
        # All intervals should be supported for Gate.io
        for interval in INTERVALS:
            assert interval in ws_intervals