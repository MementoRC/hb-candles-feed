"""
Tests for the AscendExSpotAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.ascend_ex.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.adapters.ascend_ex.spot_adapter import AscendExSpotAdapter
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestAscendExSpotAdapter(BaseAdapterTest):
    """Test suite for the AscendExSpotAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return AscendExSpotAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair.replace("-", "/")

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
            "n": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        """Return the expected full REST params for the adapter."""
        params = {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "n": limit,
            # "to": end_time * 1000,  # Excluded: end_time is no longer part of the fetch_rest_candles protocol
        }
        # AscendEx doesn't use startTime in its API, and 'to' (end_time) is also excluded by protocol.
        return params

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "op": "sub",
            "ch": f"bar:{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}:{self.get_expected_trading_pair_format(trading_pair)}",
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return {
            "status": "ok",
            "data": [
                {
                    "data": {
                        "ts": base_time,  # Open time in milliseconds
                        "o": "50000.0",  # Open
                        "h": "51000.0",  # High
                        "l": "49000.0",  # Low
                        "c": "50500.0",  # Close
                        "v": "5000000.0",  # Quote asset volume
                    }
                },
                {
                    "data": {
                        "ts": base_time + 60000,  # Open time in milliseconds
                        "o": "50500.0",  # Open
                        "h": "52000.0",  # High
                        "l": "50000.0",  # Low
                        "c": "51500.0",  # Close
                        "v": "7500000.0",  # Quote asset volume
                    }
                },
            ],
        }

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return {
            "m": "bar",
            "data": {
                "ts": base_time,  # Timestamp in milliseconds
                "o": "50000.0",  # Open
                "h": "51000.0",  # High
                "l": "49000.0",  # Low
                "c": "50500.0",  # Close
                "v": "5000000.0",  # Quote asset volume
            },
        }

    # Additional test cases specific to AscendExSpotAdapter

    def test_ascendex_specific_timestamp_handling(self, adapter):
        """Test AscendEx-specific timestamp handling."""
        # AscendEx uses milliseconds for timestamps
        assert adapter.TIMESTAMP_UNIT == "milliseconds"

        # Test conversion
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC
        timestamp_ms = timestamp_seconds * 1000

        # Convert to exchange format (should be in milliseconds)
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_ms

        # Convert from exchange format (should be in seconds)
        assert adapter.ensure_timestamp_in_seconds(timestamp_ms) == timestamp_seconds

    def test_ascendex_specific_trading_pair_format(self, adapter):
        """Test AscendEx-specific trading pair format."""
        # Test various trading pair formats
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC/USDT"
        assert adapter.get_trading_pair_format("ETH-BTC") == "ETH/BTC"
        assert adapter.get_trading_pair_format("SOL-USDT") == "SOL/USDT"

        # Test with lowercase
        assert adapter.get_trading_pair_format("btc-usdt") == "btc/usdt"

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

    def test_ws_subscription_payload_format(self, adapter):
        """Test the format of WebSocket subscription payload."""
        trading_pair = "BTC-USDT"
        interval = "1m"

        payload = adapter.get_ws_subscription_payload(trading_pair, interval)

        assert payload["op"] == "sub"
        assert payload["ch"] == f"bar:{INTERVAL_TO_EXCHANGE_FORMAT[interval]}:BTC/USDT"

        # Test with different intervals
        for interval_name in ["5m", "15m", "1h", "1d"]:
            payload = adapter.get_ws_subscription_payload(trading_pair, interval_name)
            assert payload["ch"] == f"bar:{INTERVAL_TO_EXCHANGE_FORMAT[interval_name]}:BTC/USDT"

    def test_parse_ws_message_ping(self, adapter):
        """Test parsing ping WebSocket message."""
        # Sample AscendEx ping message
        ws_message = {
            "m": "ping",
            "data": {
                "ts": 1672531200000  # 2023-01-01 00:00:00 UTC in milliseconds
            },
        }

        candles = adapter.parse_ws_message(ws_message)
        # Ping messages should be ignored, returning None
        assert candles is None

    def test_get_rest_url(self, adapter):
        """Test REST URL method."""
        assert adapter._get_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def test_get_ws_url(self, adapter):
        """Test WebSocket URL method."""
        assert adapter.get_ws_url() == SPOT_WSS_URL
