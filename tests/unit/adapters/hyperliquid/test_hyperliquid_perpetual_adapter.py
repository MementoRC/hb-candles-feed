"""
Tests for the HyperliquidPerpetualAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.hyperliquid.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    PERP_WSS_URL,
    REST_URL,
    WS_INTERVALS,
)
from candles_feed.adapters.hyperliquid.perpetual_adapter import HyperliquidPerpetualAdapter
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestHyperliquidPerpetualAdapter(BaseAdapterTest):
    """Test suite for the HyperliquidPerpetualAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return HyperliquidPerpetualAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        # HyperLiquid only uses the base asset
        return trading_pair.split("-")[0]

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return REST_URL

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return PERP_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "type": "candles",
            "coin": trading_pair.split("-")[0],
            "resolution": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        params = self.get_expected_rest_params_minimal(trading_pair, interval)
        params.update({
            "limit": limit,
            "startTime": start_time,
            "endTime": end_time,
        })
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

    # Additional test cases specific to HyperliquidPerpetualAdapter
    def test_hyperliquid_specific_trading_pair_format(self, adapter):
        """Test HyperLiquid-specific trading pair format behavior."""
        # Test standard case - HyperLiquid only uses the base asset
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC"

        # Test with multiple hyphens
        assert adapter.get_trading_pair_format("ETH-BTC-PERP") == "ETH"

    def test_hyperliquid_specific_rest_params(self, adapter):
        """Test HyperLiquid-specific REST parameters."""
        trading_pair = "BTC-USDT"
        interval = "1m"

        # Check the 'type' parameter is added
        params = adapter._get_rest_params(trading_pair, interval)
        assert params["type"] == "candles"

    def test_hyperliquid_intervals_mapping(self, adapter):
        """Test HyperLiquid-specific interval mapping."""
        # Verify intervals match constants
        assert adapter.get_supported_intervals() == INTERVALS
        assert adapter.get_ws_supported_intervals() == WS_INTERVALS

    @pytest.mark.asyncio
    async def test_hyperliquid_error_handling(self, adapter):
        """Test HyperLiquid-specific error handling."""
        # Create a mock network client
        mock_client = MagicMock()
        mock_client.get_rest_data = AsyncMock(side_effect=Exception("API Error"))

        # Test error handling during fetch
        with pytest.raises(Exception):
            await adapter.fetch_rest_candles(
                trading_pair="BTC-USDT",
                interval="1m",
                network_client=mock_client
            )
