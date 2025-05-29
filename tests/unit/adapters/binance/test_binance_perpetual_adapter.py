"""
Tests for the BinancePerpetualAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.binance.constants import (  # noqa: F401, used in BaseAdapterTest
    INTERVAL_TO_EXCHANGE_FORMAT,  # noqa: F401, used in BaseAdapterTest
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from candles_feed.adapters.binance.perpetual_adapter import BinancePerpetualAdapter
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestBinancePerpetualAdapter(BaseAdapterTest):
    """Test suite for the BinancePerpetualAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return BinancePerpetualAdapter()

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
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
            "startTime": start_time * 1000,  # Convert to milliseconds
            "endTime": end_time * 1000,  # Convert to milliseconds
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "method": "SUBSCRIBE",
            "params": [
                f"{self.get_expected_trading_pair_format(trading_pair).lower()}@kline_{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}"
            ],
            "id": 1,
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return [
            [
                base_time,  # Open time
                "50000.0",  # Open
                "51000.0",  # High
                "49000.0",  # Low
                "50500.0",  # Close
                "100.0",  # Volume
                base_time + 59999,  # Close time
                "5000000.0",  # Quote asset volume
                1000,  # Number of trades
                "60.0",  # Taker buy base asset volume
                "3000000.0",  # Taker buy quote asset volume
                "0",  # Ignore
            ],
            [
                base_time + 60000,  # Open time
                "50500.0",  # Open
                "52000.0",  # High
                "50000.0",  # Low
                "51500.0",  # Close
                "150.0",  # Volume
                base_time + 119999,  # Close time
                "7500000.0",  # Quote asset volume
                1500,  # Number of trades
                "90.0",  # Taker buy base asset volume
                "4500000.0",  # Taker buy quote asset volume
                "0",  # Ignore
            ],
        ]

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return {
            "e": "kline",  # Event type
            "E": base_time + 100,  # Event time
            "s": "BTCUSDT",  # Symbol
            "k": {
                "t": base_time,  # Kline start time
                "T": base_time + 59999,  # Kline close time
                "s": "BTCUSDT",  # Symbol
                "i": "1m",  # Interval
                "f": 100,  # First trade ID
                "L": 200,  # Last trade ID
                "o": "50000.0",  # Open price
                "c": "50500.0",  # Close price
                "h": "51000.0",  # High price
                "l": "49000.0",  # Low price
                "v": "100.0",  # Base asset volume
                "n": 1000,  # Number of trades
                "x": False,  # Is this kline closed?
                "q": "5000000.0",  # Quote asset volume
                "V": "60.0",  # Taker buy base asset volume
                "Q": "3000000.0",  # Taker buy quote asset volume
                "B": "0",  # Ignore
            },
        }

    # Additional test cases specific to BinancePerpetualAdapter

    def test_binance_specific_timestamp_handling(self, adapter):
        """Test Binance-specific timestamp handling."""
        # Binance uses milliseconds for timestamps
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

    def test_get_ws_url(self, adapter):
        """Test WebSocket URL retrieval."""
        # Test both the instance method and the internal static method
        assert adapter.get_ws_url() == PERPETUAL_WSS_URL
        assert BinancePerpetualAdapter._get_ws_url() == PERPETUAL_WSS_URL
