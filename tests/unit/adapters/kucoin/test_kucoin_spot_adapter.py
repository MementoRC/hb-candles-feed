"""
Unit tests for the KucoinSpotAdapter class.
"""

import contextlib
from datetime import datetime, timezone
from unittest import mock
from unittest.mock import patch

import pytest

from candles_feed.adapters.kucoin.constants import (  # noqa: F401, used in BaseAdapterTest
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.adapters.kucoin.spot_adapter import KucoinSpotAdapter
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestKucoinSpotAdapter(BaseAdapterTest):
    """Test suite for the KucoinSpotAdapter class using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return KucoinSpotAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        # KuCoin doesn't change the format
        return trading_pair

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
            "type": interval,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "type": interval,
            "limit": limit,
            "startAt": start_time * 1000,  # KuCoin uses milliseconds
            # "endAt": end_time * 1000,  # Excluded: end_time is no longer part of the fetch_rest_candles protocol
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        # For KuCoin we need to check key presence rather than exact values since ID is dynamic
        return {
            "type": "subscribe",
            "topic": f"/market/candles:{trading_pair}_{interval}",
            "privateChannel": False,
            "response": True,
        }

    # Override the BaseAdapterTest method for WebSocket subscription payload
    # KuCoin has a dynamic ID field we need to handle specially
    def test_get_ws_subscription_payload(self, adapter, trading_pair, interval):
        """Test WebSocket subscription payload generation."""
        payload = adapter.get_ws_subscription_payload(trading_pair, interval)

        # Verify structure
        assert isinstance(payload, dict)
        assert "id" in payload
        assert isinstance(payload["id"], int)
        assert payload["type"] == "subscribe"
        assert payload["topic"] == f"/market/candles:{trading_pair}_{interval}"
        assert payload["privateChannel"] is False
        assert payload["response"] is True

    # Additional tests specific to KuCoin spot adapter
    def test_kucoin_specific_rest_response_parsing(self, adapter):
        """Test KuCoin-specific REST response parsing."""
        # Create a custom response in KuCoin format
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        response = {
            "code": "200000",
            "data": [
                [
                    str(base_time * 1000),  # KuCoin uses millisecond strings
                    "50000.0",  # open
                    "51000.0",  # high
                    "49000.0",  # low
                    "50500.0",  # close
                    "100.0",  # volume
                    "5000000.0",  # quote volume
                ],
                [
                    str((base_time + 60) * 1000),
                    "50500.0",  # open
                    "52000.0",  # high
                    "50000.0",  # low
                    "51500.0",  # close
                    "150.0",  # volume
                    "7500000.0",  # quote volume
                ],
            ],
        }

        candles = adapter._parse_rest_response(response)

        # Verify response parsing
        assert len(candles) == 2

        # Check first candle
        assert candles[0].timestamp == 1672531200  # 2023-01-01 00:00:00 UTC in seconds
        assert candles[0].open == 50000.0
        assert candles[0].high == 51000.0
        assert candles[0].low == 49000.0
        assert candles[0].close == 50500.0
        assert candles[0].volume == 100.0
        assert candles[0].quote_asset_volume == 5000000.0

    def test_kucoin_specific_ws_message_parsing(self, adapter):
        """Test KuCoin-specific WebSocket message parsing."""
        # Create a custom WebSocket message in KuCoin format
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        message = {
            "type": "message",
            "topic": "/market/candles:BTC-USDT_1m",
            "subject": "trade.candles.update",
            "data": {
                "symbol": "BTC-USDT",
                "candles": [
                    str(base_time * 1000),  # KuCoin uses millisecond strings
                    "50000.0",  # open
                    "50500.0",  # close
                    "51000.0",  # high
                    "49000.0",  # low
                    "100.0",  # volume
                    "5000000.0",  # quote volume
                ],
                "time": base_time * 1000,
            },
        }

        candles = adapter.parse_ws_message(message)

        # Verify message parsing
        assert candles is not None
        assert len(candles) == 1

        candle = candles[0]
        assert candle.timestamp == 1672531200  # 2023-01-01 00:00:00 UTC in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        # Use the fixture format defined in conftest.py
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        return {
            "code": "200000",
            "data": [
                [
                    str(base_time * 1000),  # KuCoin uses milliseconds strings
                    "50000.0",  # open
                    "51000.0",  # high
                    "49000.0",  # low
                    "50500.0",  # close
                    "100.0",  # volume
                    "5000000.0",  # quote volume
                ],
                [
                    str((base_time + 60) * 1000),  # Next candle 60 seconds later
                    "50500.0",  # open
                    "52000.0",  # high
                    "50000.0",  # low
                    "51500.0",  # close
                    "150.0",  # volume
                    "7500000.0",  # quote volume
                ],
            ],
        }

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        # Use the fixture format defined in conftest.py
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        return {
            "type": "message",
            "topic": "/market/candles:BTC-USDT_1m",
            "subject": "trade.candles.update",
            "data": {
                "symbol": "BTC-USDT",
                "candles": [
                    str(base_time * 1000),  # KuCoin uses milliseconds strings
                    "50000.0",  # open
                    "50500.0",  # close
                    "51000.0",  # high
                    "49000.0",  # low
                    "100.0",  # volume
                    "5000000.0",  # quote volume
                ],
                "time": base_time * 1000,
            },
        }

    # Additional test cases specific to KucoinSpotAdapter

    def test_timestamp_in_milliseconds(self, adapter):
        """Test that timestamps are correctly handled in milliseconds."""
        assert adapter.TIMESTAMP_UNIT == "milliseconds"

        # Test timestamp conversion methods
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC

        # To exchange should convert to milliseconds
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_seconds * 1000

        # Ensure timestamp is in seconds regardless of input format
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds * 1000) == timestamp_seconds
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds) == timestamp_seconds
        assert (
            adapter.ensure_timestamp_in_seconds(str(timestamp_seconds * 1000)) == timestamp_seconds
        )

    @patch("time.time")
    def test_websocket_subscription_id(self, mock_time, adapter):
        """Test that WebSocket subscription ID is based on current time."""
        fixed_time = 1622505600.0
        mock_time.return_value = fixed_time

        payload = adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        assert payload["id"] == int(fixed_time * 1000)  # Should be current time in milliseconds

    # Override the BaseAdapterTest method for WebSocket supported intervals
    # KuCoin is special because it only supports 1m interval for WebSocket
    def test_get_ws_supported_intervals(self, adapter):
        """Test getting WebSocket supported intervals."""
        ws_intervals = adapter.get_ws_supported_intervals()

        # Basic validation
        assert isinstance(ws_intervals, list)

        # For KuCoin, we only expect 1m interval
        assert ws_intervals == ["1m"]

    # Override the BaseAdapterTest method for async test
    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async(self, adapter, trading_pair, interval):
        """Custom test for fetch_rest_candles_async for KuCoin."""
        # Skip test for SyncOnlyAdapter adapters
        with contextlib.suppress(ImportError):
            from candles_feed.adapters.adapter_mixins import SyncOnlyAdapter

            if isinstance(adapter, SyncOnlyAdapter):
                pytest.skip("Test only applicable for async adapters")

        # Create a custom mock response
        mock_response = self.get_mock_candlestick_response()

        # Create a mock network client
        mock_client = mock.MagicMock()
        mock_client.get_rest_data = mock.AsyncMock(return_value=mock_response)

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

        # Verify that params were passed (without exact comparison)
        assert "symbol" in kwargs["params"]
        assert kwargs["params"]["symbol"] == trading_pair
