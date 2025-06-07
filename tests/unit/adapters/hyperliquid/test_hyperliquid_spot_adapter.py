"""
Tests for the HyperliquidSpotAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.hyperliquid.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    SPOT_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.adapters.hyperliquid.spot_adapter import HyperliquidSpotAdapter
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestHyperliquidSpotAdapter(BaseAdapterTest):
    """Test suite for the HyperliquidSpotAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return HyperliquidSpotAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        # HyperLiquid only uses the base asset
        return trading_pair.split("-")[0]

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return REST_URL

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return SPOT_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "type": "candles",
            "coin": trading_pair.split("-")[0],
            "resolution": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        """Return the expected full REST params for the adapter."""
        params = self.get_expected_rest_params_minimal(trading_pair, interval)
        params.update(
            {
                "limit": limit,
                "startTime": start_time,
                # "endTime": end_time,  # Excluded: end_time is no longer part of the fetch_rest_candles protocol
            }
        )
        return params

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "method": "subscribe",
            "channel": "candles",
            "coin": trading_pair.split("-")[0],
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
            "channel": "candles",
            "data": [base_time, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", "5000000.0"],
        }

    # Additional test cases specific to HyperliquidSpotAdapter
    def test_hyperliquid_specific_trading_pair_format(self, adapter):
        """Test HyperLiquid-specific trading pair format behavior."""
        # Test standard case - HyperLiquid only uses the base asset
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC"

        # Test with multiple hyphens
        assert adapter.get_trading_pair_format("ETH-BTC-PERP") == "ETH"

    @pytest.mark.asyncio
    async def test_hyperliquid_rest_get_implementation(self, adapter):
        """Test HyperLiquid's fetch_rest_candles implementation."""
        # Create a mock network client
        mock_client = MagicMock()
        mock_client.get_rest_data = AsyncMock(return_value=self.get_mock_candlestick_response())

        # Define test parameters
        trading_pair = "BTC-USDT"
        interval = "1m"

        # Test the method with our mock
        candles = await adapter.fetch_rest_candles(
            trading_pair=trading_pair, interval=interval, network_client=mock_client
        )

        # Verify the result
        assert len(candles) == 2

        # Check that the mock was called with the correct parameters
        mock_client.get_rest_data.assert_called_once()
        args, kwargs = mock_client.get_rest_data.call_args
        assert kwargs["url"] == adapter._get_rest_url()
        assert kwargs["params"] == adapter._get_rest_params(trading_pair, interval)

    def test_hyperliquid_intervals_mapping(self, adapter):
        """Test HyperLiquid-specific interval mapping."""
        # Verify intervals match constants
        assert adapter.get_supported_intervals() == INTERVALS
        assert adapter.get_ws_supported_intervals() == WS_INTERVALS

    def test_hyperliquid_parse_rest_response_details(self, adapter):
        """Test HyperLiquid-specific response parsing details."""
        # Test with a minimal valid response
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        minimal_response = [
            [timestamp, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", "5000000.0"]
        ]

        candles = adapter._parse_rest_response(minimal_response)
        assert len(candles) == 1
        assert candles[0].timestamp == timestamp
        assert candles[0].open == 50000.0
        assert candles[0].high == 51000.0
        assert candles[0].low == 49000.0
        assert candles[0].close == 50500.0
        assert candles[0].volume == 100.0
        assert candles[0].quote_asset_volume == 5000000.0

        # Test with invalid data format
        invalid_response = [{"wrong": "format"}]
        candles = adapter._parse_rest_response(invalid_response)
        assert candles == []
