"""
Tests for the OKXBaseAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.okx.base_adapter import (
    OKXBaseAdapter,  # noqa: F401, used in BaseAdapterTest
)
from candles_feed.adapters.okx.constants import (  # noqa: F401, used in BaseAdapterTest
    INTERVAL_TO_EXCHANGE_FORMAT,  # noqa: F401, used in BaseAdapterTest
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
)
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


# Concrete implementation of OKXBaseAdapter for testing
class ConcreteOKXAdapter(OKXBaseAdapter):
    """Concrete implementation of OKXBaseAdapter for testing."""

    @staticmethod
    def _get_rest_url() -> str:
        return "https://test.okx.com/api/v5/market/candles"

    @staticmethod
    def _get_ws_url() -> str:
        return "wss://test.okx.com/ws/v5/public"


class TestOKXBaseAdapter(BaseAdapterTest):
    """Test suite for the OKXBaseAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return ConcreteOKXAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair  # OKX preserves the format, just uses / instead of - for API calls

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return "https://test.okx.com/api/v5/market/candles"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return "wss://test.okx.com/ws/v5/public"

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "instId": trading_pair.replace("-", "/"),  # OKX uses / in API calls
            "bar": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        # OKX uses after and before parameters with timestamps
        return {
            "instId": trading_pair.replace("-", "/"),
            "bar": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
            "after": start_time * 1000,  # Convert to milliseconds
            "before": end_time * 1000,  # Convert to milliseconds
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "op": "subscribe",
            "args": [
                {
                    "channel": f"candle{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}",
                    "instId": trading_pair.replace("-", "/"),
                }
            ],
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return {
            "code": "0",
            "msg": "",
            "data": [
                [
                    str(base_time),  # Time
                    "50000.0",  # Open
                    "51000.0",  # High
                    "49000.0",  # Low
                    "50500.0",  # Close
                    "100.0",  # Volume
                    "5000000.0",  # Quote asset volume
                ],
                [
                    str(base_time + 60000),  # Time
                    "50500.0",  # Open
                    "52000.0",  # High
                    "50000.0",  # Low
                    "51500.0",  # Close
                    "150.0",  # Volume
                    "7500000.0",  # Quote asset volume
                ],
            ],
        }

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return {
            "arg": {"channel": "candle1m", "instId": "BTC/USDT"},
            "data": [
                [
                    str(base_time),  # Time
                    "50000.0",  # Open
                    "51000.0",  # High
                    "49000.0",  # Low
                    "50500.0",  # Close
                    "100.0",  # Volume
                    "5000000.0",  # Quote asset volume
                ]
            ],
        }

    # Additional test cases specific to OKXBaseAdapter

    def test_okx_base_concrete_implementation(self, adapter):
        """Test that a concrete implementation of OKXBaseAdapter works."""
        # Verify the concrete adapter was created correctly
        assert isinstance(adapter, ConcreteOKXAdapter)
        assert adapter._get_rest_url() == "https://test.okx.com/api/v5/market/candles"
        assert adapter._get_ws_url() == "wss://test.okx.com/ws/v5/public"

    def test_okx_specific_timestamp_handling(self, adapter):
        """Test OKX-specific timestamp handling."""
        # OKX uses milliseconds for timestamps
        assert adapter.TIMESTAMP_UNIT == "milliseconds"

        # Test conversion
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC
        timestamp_ms = timestamp_seconds * 1000

        # Convert to exchange format (should be in milliseconds)
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_ms

        # Convert from exchange format (should be in seconds)
        assert adapter.ensure_timestamp_in_seconds(timestamp_ms) == timestamp_seconds

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
