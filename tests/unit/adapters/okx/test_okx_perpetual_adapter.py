"""
Tests for the OKXPerpetualAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.okx.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from candles_feed.adapters.okx.perpetual_adapter import OKXPerpetualAdapter
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestOKXPerpetualAdapter(BaseAdapterTest):
    """Test suite for the OKXPerpetualAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return OKXPerpetualAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        # For perpetual contracts, OKX requires the SWAP suffix to be added
        if trading_pair.endswith("-SWAP"):
            return trading_pair
        return f"{trading_pair}-SWAP"

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return PERPETUAL_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        # For minimal params, we don't need to add -SWAP suffix as the adapter will do that
        # The adapter uses the original trading_pair format for parameter generation
        return {
            "instId": trading_pair.replace("-", "/"),  # OKX uses / in API calls
            "bar": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        # OKX uses after and before parameters with timestamps
        # The adapter uses the original trading_pair format for parameter generation
        return {
            "instId": trading_pair.replace("-", "/"),
            "bar": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
            "after": start_time * 1000,  # Convert to milliseconds
            "before": end_time * 1000,  # Convert to milliseconds
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        # For WebSocket, we don't add -SWAP suffix as the adapter will do that
        # The adapter uses the original trading_pair format for subscription payload
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

    # Additional test cases specific to OKXPerpetualAdapter

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

    def test_okx_perpetual_trading_pair_format(self, adapter):
        """Test OKX perpetual-specific trading pair format."""
        # Test various trading pair formats
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC-USDT-SWAP"
        assert adapter.get_trading_pair_format("ETH-USDT") == "ETH-USDT-SWAP"

        # If already has SWAP suffix, should return as is
        assert adapter.get_trading_pair_format("BTC-USDT-SWAP") == "BTC-USDT-SWAP"

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
