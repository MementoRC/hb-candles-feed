"""
Tests for the GateIoPerpetualAdapter using the base adapter test class.
"""

from datetime import UTC, datetime, timezone
from unittest import mock

import pytest

from candles_feed.adapters.gate_io.constants import (  # noqa: F401, used in BaseAdapterTest
    INTERVAL_TO_EXCHANGE_FORMAT,  # noqa: F401, used in BaseAdapterTest
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_CHANNEL_NAME,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from candles_feed.adapters.gate_io.perpetual_adapter import GateIoPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestGateIoPerpetualAdapter(BaseAdapterTest):
    """Test suite for the GateIoPerpetualAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return GateIoPerpetualAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair.replace("-", "_")

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return PERPETUAL_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "contract": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "contract": self.get_expected_trading_pair_format(trading_pair),
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
                f"{PERPETUAL_CHANNEL_NAME}",
                {
                    "currency_pair": self.get_expected_trading_pair_format(trading_pair),
                    "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
                },
            ],
            "id": 12345,
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp())

        # Futures REST rows are dicts: t, v (contracts), c, h, l, o, sum (quote)
        return [
            {
                "t": base_time,
                "v": 100,
                "c": "50500.0",
                "h": "51000.0",
                "l": "49000.0",
                "o": "50000.0",
                "sum": "5000000.0",
            },
            {
                "t": base_time + 60,
                "v": 150,
                "c": "51500.0",
                "h": "52000.0",
                "l": "50000.0",
                "o": "50500.0",
                "sum": "7500000.0",
            },
        ]

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp())

        return {
            "time": base_time,
            "channel": PERPETUAL_CHANNEL_NAME,
            "event": "update",
            "result": [
                {
                    "t": base_time,
                    "v": 100,
                    "c": "50500.0",
                    "h": "51000.0",
                    "l": "49000.0",
                    "o": "50000.0",
                    "n": "1m_BTC_USDT",
                    "a": "5000000.0",
                }
            ],
        }

    # Additional test cases specific to GateIoPerpetualAdapter

    def test_rest_dict_row_mapping(self, adapter):
        """Futures dict rows must map to the right CandleData fields."""
        (candle, _) = adapter._parse_rest_response(self.get_mock_candlestick_response())

        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0

    def test_ws_list_result_mapping(self, adapter):
        """Futures WS list-of-dict result must map to the right fields."""
        (candle,) = adapter.parse_ws_message(self.get_mock_websocket_message())

        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0

    def test_perpetual_specific_features(self, adapter):
        """Test perpetual-specific features."""
        # Verify that the adapter uses perpetual-specific URLs
        assert PERPETUAL_REST_URL in adapter._get_rest_url()
        assert adapter._get_ws_url() == PERPETUAL_WSS_URL

    def test_gate_io_channel_name(self, adapter):
        """Test Gate.io channel name getter."""
        assert adapter.get_channel_name() == PERPETUAL_CHANNEL_NAME

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
