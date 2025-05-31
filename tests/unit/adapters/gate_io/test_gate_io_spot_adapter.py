"""
Tests for the GateIoSpotAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest import mock

import pytest

from candles_feed.adapters.gate_io.constants import (  # noqa: F401, used in BaseAdapterTest
    INTERVAL_TO_EXCHANGE_FORMAT,  # noqa: F401, used in BaseAdapterTest
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_CHANNEL_NAME,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.adapters.gate_io.spot_adapter import GateIoSpotAdapter
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestGateIoSpotAdapter(BaseAdapterTest):
    """Test suite for the GateIoSpotAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return GateIoSpotAdapter()

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
            # "to": end_time,  # Excluded: end_time is no longer part of the fetch_rest_candles protocol
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
                str(base_time),  # timestamp
                "50000.0",  # open
                "50500.0",  # close
                "49000.0",  # low
                "51000.0",  # high
                "100.0",  # volume
                "5000000.0",  # quote currency volume
                "BTC_USDT",  # currency pair
            ],
            [
                str(base_time + 60),  # timestamp
                "50500.0",  # open
                "51500.0",  # close
                "50000.0",  # low
                "52000.0",  # high
                "150.0",  # volume
                "7500000.0",  # quote currency volume
                "BTC_USDT",  # currency pair
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
                    "50000.0",  # open
                    "50500.0",  # close
                    "49000.0",  # low
                    "51000.0",  # high
                    "100.0",  # volume
                    "5000000.0",  # quote currency volume
                    "BTC_USDT",  # currency pair
                ],
            ],
        }

    # Additional test cases specific to GateIoSpotAdapter

    def test_gate_io_specific_timestamp_handling(self, adapter):
        """Test Gate.io-specific timestamp handling."""
        # Gate.io uses seconds for timestamps
        assert adapter.TIMESTAMP_UNIT == "seconds"

        # Test conversion
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC

        # Convert to exchange format (should be in seconds)
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_seconds

        # Convert from exchange format (should be in seconds)
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds) == timestamp_seconds

    def test_gate_io_specific_trading_pair_format(self, adapter):
        """Test Gate.io-specific trading pair format."""
        # Test various trading pair formats
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC_USDT"
        assert adapter.get_trading_pair_format("ETH-BTC") == "ETH_BTC"
        assert adapter.get_trading_pair_format("SOL-USDT") == "SOL_USDT"

        # Test with lowercase
        assert adapter.get_trading_pair_format("btc-usdt") == "btc_usdt"

    def test_gate_io_channel_name(self, adapter):
        """Test Gate.io channel name getter."""
        assert adapter.get_channel_name() == SPOT_CHANNEL_NAME

    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async(self, adapter, trading_pair, interval):
        """Test fetch_rest_candles async method."""
        # Create a mock network client
        mock_client = mock.MagicMock()
        mock_client.get_rest_data = mock.AsyncMock(
            return_value=self.get_mock_candlestick_response()
        )

        # Call the async method
        candles = await adapter.fetch_rest_candles(
            trading_pair, interval, network_client=mock_client
        )

        # Basic validation
        assert isinstance(candles, list)
        assert all(isinstance(candle, CandleData) for candle in candles)
        assert len(candles) > 0

        # Verify the network client was called correctly
        mock_client.get_rest_data.assert_called_once()
        args, kwargs = mock_client.get_rest_data.call_args
        assert kwargs["url"] == adapter._get_rest_url()
        # Verify params match expected values
        expected_params = adapter._get_rest_params(trading_pair, interval)
        assert kwargs["params"] == expected_params
