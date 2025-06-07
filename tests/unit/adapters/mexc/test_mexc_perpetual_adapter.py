"""
Unit tests for the MEXCPerpetualAdapter class using the BaseAdapterTest class.
"""

import contextlib
from datetime import datetime, timezone
from unittest import mock

import pytest

from candles_feed.adapters.mexc.constants import (  # noqa: F401, used in BaseAdapterTest
    INTERVAL_TO_PERPETUAL_FORMAT,  # noqa: F401, used in BaseAdapterTest
    INTERVALS,  # noqa: F401, used in BaseAdapterTest
    PERP_KLINE_TOPIC,
    PERP_REST_URL,
    PERP_WSS_URL,
    SUB_ENDPOINT_NAME,
    WS_INTERVALS,
)
from candles_feed.adapters.mexc.perpetual_adapter import MEXCPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestMEXCPerpetualAdapter(BaseAdapterTest):
    """Test suite for the MEXCPerpetualAdapter class using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return MEXCPerpetualAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair.replace("-", "_")

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return PERP_REST_URL

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return PERP_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_PERPETUAL_FORMAT.get(interval),
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_PERPETUAL_FORMAT.get(interval),
            "size": limit,
            "start": start_time,  # MEXC perpetual uses seconds
            # "end": end_time,  # Excluded: end_time is no longer part of the fetch_rest_candles protocol
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        symbol = self.get_expected_trading_pair_format(trading_pair).replace("_", "").lower()
        mexc_interval = INTERVAL_TO_PERPETUAL_FORMAT.get(interval, interval)

        return {
            "method": SUB_ENDPOINT_NAME,
            "params": [f"{PERP_KLINE_TOPIC}{mexc_interval}_{symbol}"],
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(
            datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()
        )  # In seconds for perpetual

        return {
            "success": True,
            "code": 0,
            "data": [
                {
                    "time": base_time,
                    "open": "50000.0",
                    "close": "50500.0",
                    "high": "51000.0",
                    "low": "49000.0",
                    "vol": "100.0",
                    "amount": "5000000.0",
                },
                {
                    "time": base_time + 60,
                    "open": "50500.0",
                    "close": "51500.0",
                    "high": "52000.0",
                    "low": "50000.0",
                    "vol": "150.0",
                    "amount": "7500000.0",
                },
            ],
        }

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(
            datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()
        )  # In seconds for perpetual

        return {
            "channel": "push.kline",
            "data": {
                "a": "5000000.0",  # amount (quote volume)
                "c": "50500.0",  # close
                "h": "51000.0",  # high
                "interval": "Min1",  # interval
                "l": "49000.0",  # low
                "o": "50000.0",  # open
                "q": "0",  # ignore
                "symbol": "BTC_USDT",  # symbol
                "t": base_time,  # timestamp
                "v": "100.0",  # volume
            },
            "symbol": "BTC_USDT",
        }

    # Additional test cases specific to MEXCPerpetualAdapter

    def test_custom_trading_pair_format(self, adapter):
        """Test trading pair format for various cases."""
        # Test with multiple hyphens
        assert adapter.get_trading_pair_format("BTC-USDT-PERP") == "BTC_USDT_PERP"

        # Test with lowercase
        assert adapter.get_trading_pair_format("btc-usdt") == "btc_usdt"

    def test_get_kline_topic(self, adapter):
        """Test kline topic retrieval."""
        assert adapter.get_kline_topic() == PERP_KLINE_TOPIC

    def test_get_interval_format(self, adapter):
        """Test getting interval format."""
        # Test standard intervals
        assert adapter.get_interval_format("1m") == "Min1"
        assert adapter.get_interval_format("1h") == "Min60"
        assert adapter.get_interval_format("1d") == "Day1"

        # Test fallback
        assert adapter.get_interval_format("unknown") == "unknown"

    def test_supported_intervals(self, adapter):
        """Test getting supported intervals."""
        intervals = adapter.get_supported_intervals()

        # Verify intervals match the expected values
        assert intervals == INTERVALS
        assert "1m" in intervals
        assert intervals["1m"] == 60
        assert "1h" in intervals
        assert intervals["1h"] == 3600
        assert "1d" in intervals
        assert intervals["1d"] == 86400

    def test_ws_supported_intervals(self, adapter):
        """Test getting WebSocket supported intervals."""
        ws_intervals = adapter.get_ws_supported_intervals()

        # Verify WS intervals match the expected values
        assert ws_intervals == WS_INTERVALS
        assert "1m" in ws_intervals
        assert "1h" in ws_intervals

    def test_parse_rest_response_field_mapping(self, adapter):
        """Test field mapping for REST API response parsing."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        # Create a mock response data
        response = {
            "success": True,
            "code": 0,
            "data": [
                {
                    "time": timestamp,
                    "open": "50000.0",
                    "close": "50500.0",
                    "high": "51000.0",
                    "low": "49000.0",
                    "vol": "100.0",
                    "amount": "5000000.0",
                }
            ],
        }

        candles = adapter._parse_rest_response(response)

        # Verify correct parsing
        assert len(candles) == 1
        candle = candles[0]

        # Verify field mapping
        assert candle.timestamp == timestamp  # Should already be in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0

    def test_parse_ws_message_field_mapping(self, adapter):
        """Test field mapping for WebSocket message parsing."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

        # Create a mock WebSocket message
        message = {
            "channel": "push.kline",
            "data": {
                "a": "5000000.0",  # amount (quote volume)
                "c": "50500.0",  # close
                "h": "51000.0",  # high
                "interval": "Min1",  # interval
                "l": "49000.0",  # low
                "o": "50000.0",  # open
                "q": "0",  # ignore
                "symbol": "BTC_USDT",  # symbol
                "t": timestamp,  # timestamp
                "v": "100.0",  # volume
            },
            "symbol": "BTC_USDT",
        }

        candles = adapter.parse_ws_message(message)

        # Verify correct parsing
        assert candles is not None
        assert len(candles) == 1
        candle = candles[0]

        # Verify field mapping
        assert candle.timestamp == timestamp  # Should already be in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0

    def test_parse_ws_message_invalid(self, adapter):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"channel": "push.ticker", "data": "some_data"}
        candles = adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = adapter.parse_ws_message(None)
        assert candles is None

        # Test with missing data
        ws_message = {"channel": "push.kline"}
        candles = adapter.parse_ws_message(ws_message)
        assert candles is None

    def test_timestamp_conversion(self, adapter):
        """Test timestamp conversion in MEXC format."""
        # For perpetual adapter, MEXC already uses seconds
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC

        # To exchange should keep as seconds for perpetual
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_seconds

        # Ensure timestamp is in seconds regardless of input format
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds) == timestamp_seconds
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds * 1000) == timestamp_seconds

    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async(self, adapter, trading_pair, interval):
        """Test fetch_rest_candles async method for MEXCPerpetualAdapter."""
        # Skip test for SyncOnlyAdapter adapters
        with contextlib.suppress(ImportError):
            from candles_feed.adapters.adapter_mixins import SyncOnlyAdapter

            if isinstance(adapter, SyncOnlyAdapter):
                pytest.skip("Test only applicable for async adapters")

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

        # Just verify that params were passed without checking the exact content
        assert "params" in kwargs
        assert isinstance(kwargs["params"], dict)

    def test_parse_rest_response_invalid(self, adapter):
        """Test parsing invalid REST API response."""
        # Test with missing data field
        candles = adapter._parse_rest_response({"success": True})
        assert candles == []

        # Test with non-list data field
        candles = adapter._parse_rest_response({"success": True, "data": "not a list"})
        assert candles == []
