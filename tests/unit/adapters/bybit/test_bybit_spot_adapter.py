"""
Tests for the BybitSpotAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.bybit.constants import (  # noqa: F401, used in BaseAdapterTest
    INTERVAL_TO_EXCHANGE_FORMAT,  # noqa: F401, used in BaseAdapterTest
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.adapters.bybit.spot_adapter import BybitSpotAdapter
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestBybitSpotAdapter(BaseAdapterTest):
    """Test suite for the BybitSpotAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return BybitSpotAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair.replace("-", "")

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return SPOT_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
            "category": "spot",  # Bybit specific
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
            "start": start_time * 1000,  # Convert to milliseconds
            # "end": end_time * 1000,  # Excluded: end_time is no longer part of the fetch_rest_candles protocol
            "category": "spot",  # Bybit specific
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "op": "subscribe",
            "args": [
                f"kline.{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}.{self.get_expected_trading_pair_format(trading_pair)}"
            ],
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    [
                        str(base_time),
                        "50000.0",
                        "51000.0",
                        "49000.0",
                        "50500.0",
                        "100.0",
                        "5000000.0",
                    ],
                    [
                        str(base_time + 60000),
                        "50500.0",
                        "52000.0",
                        "50000.0",
                        "51500.0",
                        "150.0",
                        "7500000.0",
                    ],
                ],
                "category": "spot",
            },
        }

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return {
            "topic": "kline.1m.BTCUSDT",
            "data": [
                {
                    "start": base_time,
                    "end": base_time + 59999,
                    "interval": "1",
                    "open": "50000.0",
                    "close": "50500.0",
                    "high": "51000.0",
                    "low": "49000.0",
                    "volume": "100.0",
                    "turnover": "5000000.0",
                    "confirm": False,
                    "timestamp": base_time + 30000,
                }
            ],
            "ts": base_time + 30000,
            "type": "snapshot",
        }

    # Additional test cases specific to BybitSpotAdapter

    def test_bybit_specific_timestamp_handling(self, adapter):
        """Test Bybit-specific timestamp handling."""
        # Bybit uses milliseconds for timestamps
        assert adapter.TIMESTAMP_UNIT == "milliseconds"

        # Test conversion
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC
        timestamp_ms = timestamp_seconds * 1000

        # Convert to exchange format (should be in milliseconds)
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_ms

        # Convert from exchange format (should be in seconds)
        assert adapter.ensure_timestamp_in_seconds(timestamp_ms) == timestamp_seconds

    def test_category_param(self, adapter):
        """Test Bybit-specific category parameter."""
        # Bybit spot uses "spot" as category
        assert adapter.get_category_param() == "spot"

    @pytest.mark.asyncio
    async def test_fetch_rest_candles_custom(self, adapter, trading_pair, interval):
        """Custom async test for fetch_rest_candles."""
        # Create a mock network client
        mock_client = MagicMock()
        mock_client.get_rest_data = AsyncMock()

        # Configure the mock to return a specific response when called
        response_data = self.get_mock_candlestick_response()
        mock_client.get_rest_data.return_value = response_data

        # Test the method with our mock
        candles = await adapter.fetch_rest_candles(
            trading_pair=trading_pair, interval=interval, network_client=mock_client
        )

        # Verify the result
        assert len(candles) == 2

        # Check that the mock was called with the correct parameters
        url = adapter._get_rest_url()
        params = adapter._get_rest_params(trading_pair, interval)

        mock_client.get_rest_data.assert_called_once()
        args, kwargs = mock_client.get_rest_data.call_args
        assert kwargs["url"] == url
        assert kwargs["params"] == params

        # Test with multiple hyphens
        assert BybitSpotAdapter.get_trading_pair_format("BTC-USDT-PERP") == "BTCUSDTPERP"

        # Test with lowercase
        assert BybitSpotAdapter.get_trading_pair_format("btc-usdt") == "btcusdt"

    def test_get_rest_url(self, adapter):
        """Test REST URL retrieval."""
        expected_url = self.get_expected_rest_url()
        assert adapter._get_rest_url() == expected_url

    def test_get_ws_url(self, adapter):
        """Test WebSocket URL retrieval."""
        expected_url = self.get_expected_ws_url()
        assert adapter._get_ws_url() == expected_url
        assert adapter.get_ws_url() == expected_url

    def test_get_rest_params_minimal(self, adapter, trading_pair, interval):
        """Test REST params with minimal parameters."""
        expected_params = self.get_expected_rest_params_minimal(trading_pair, interval)
        actual_params = adapter._get_rest_params(trading_pair, interval)

        for key, value in expected_params.items():
            assert key in actual_params
            assert actual_params[key] == value

    def test_get_rest_params_full(self, adapter, trading_pair, interval):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        limit = 500

        expected_params = self.get_expected_rest_params_full(
            trading_pair, interval, start_time, limit
        )

        actual_params = adapter._get_rest_params(
            trading_pair, interval, start_time=start_time, limit=limit
        )

        for key, value in expected_params.items():
            assert key in actual_params
            assert actual_params[key] == value

    def test_parse_rest_response(self, adapter):
        """Test parsing REST API response."""
        mock_response = self.get_mock_candlestick_response()
        candles = adapter._parse_rest_response(mock_response)

        # Basic validation
        assert isinstance(candles, list)
        assert all(isinstance(candle, CandleData) for candle in candles)
        assert len(candles) > 0

    def test_get_ws_subscription_payload(self, adapter, trading_pair, interval):
        """Test WebSocket subscription payload generation."""
        expected_payload = self.get_expected_ws_subscription_payload(trading_pair, interval)
        actual_payload = adapter.get_ws_subscription_payload(trading_pair, interval)

        assert isinstance(actual_payload, dict)

        # Compare key parts of the payload
        for key, value in expected_payload.items():
            assert key in actual_payload
            assert actual_payload[key] == value

    def test_parse_ws_message_valid(self, adapter):
        """Test parsing valid WebSocket message."""
        mock_message = self.get_mock_websocket_message()
        candles = adapter.parse_ws_message(mock_message)

        # Basic validation
        assert candles is not None
        assert isinstance(candles, list)
        assert all(isinstance(candle, CandleData) for candle in candles)
        assert len(candles) > 0

    def test_parse_ws_message_invalid(self, adapter):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        invalid_message = {"topic": "trades", "data": "some_data"}
        candles = adapter.parse_ws_message(invalid_message)
        assert candles is None

        # Test with None
        candles = adapter.parse_ws_message(None)
        assert candles is None

    def test_get_supported_intervals(self, adapter):
        """Test getting supported intervals."""
        intervals = adapter.get_supported_intervals()

        # Basic validation
        assert isinstance(intervals, dict)
        assert len(intervals) > 0

        # Common intervals that should be supported by all exchanges
        common_intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]
        for interval in common_intervals:
            assert interval in intervals
            assert isinstance(intervals[interval], int)
            assert intervals[interval] > 0

    def test_get_ws_supported_intervals(self, adapter):
        """Test getting WebSocket supported intervals."""
        ws_intervals = adapter.get_ws_supported_intervals()

        # Basic validation
        assert isinstance(ws_intervals, list)

        # Should contain at least some common intervals
        common_intervals = ["1m", "1h"]
        for interval in common_intervals:
            assert interval in ws_intervals
