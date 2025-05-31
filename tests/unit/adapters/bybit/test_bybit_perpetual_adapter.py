"""
Tests for the BybitPerpetualAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.bybit.constants import (  # noqa: F401, used in BaseAdapterTest
    INTERVAL_TO_EXCHANGE_FORMAT,  # noqa: F401, used in BaseAdapterTest
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from candles_feed.adapters.bybit.perpetual_adapter import BybitPerpetualAdapter
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestBybitPerpetualAdapter(BaseAdapterTest):
    """Test suite for the BybitPerpetualAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return BybitPerpetualAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair.replace("-", "")

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return PERPETUAL_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
            "category": "linear",  # Bybit specific
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
            "start": start_time * 1000,  # Convert to milliseconds
            # "end": end_time * 1000,  # Excluded: end_time is no longer part of the fetch_rest_candles protocol
            "category": "linear",  # Bybit specific
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
                "category": "linear",
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

    # Additional test cases specific to BybitPerpetualAdapter

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
        """Test category param retrieval."""
        assert adapter.get_category_param() == "linear"

    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async(self, adapter, trading_pair, interval):
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
