"""
Unit tests for the MEXCSpotAdapter class using the BaseAdapterTest class.
"""

import contextlib
from datetime import datetime, timezone
from unittest import mock

import pytest

from candles_feed.adapters.mexc.constants import (  # noqa: F401, used in BaseAdapterTest
    INTERVAL_TO_EXCHANGE_FORMAT,  # noqa: F401, used in BaseAdapterTest
    INTERVALS,  # noqa: F401, used in BaseAdapterTest
    SPOT_CANDLES_ENDPOINT,
    SPOT_KLINE_TOPIC,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    SUB_ENDPOINT_NAME,
    WS_INTERVALS,
)
from candles_feed.adapters.mexc.spot_adapter import MEXCSpotAdapter
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestMEXCSpotAdapter(BaseAdapterTest):
    """Test suite for the MEXCSpotAdapter class using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return MEXCSpotAdapter()

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
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": interval,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": interval,
            "limit": limit,
            "startTime": start_time * 1000,  # MEXC uses milliseconds
            # "endTime": end_time * 1000,  # Excluded: end_time is no longer part of the fetch_rest_candles protocol
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        symbol = self.get_expected_trading_pair_format(trading_pair).replace("_", "").lower()
        mexc_interval = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)

        return {
            "method": SUB_ENDPOINT_NAME,
            "params": [f"{SPOT_KLINE_TOPIC}{mexc_interval}_{symbol}"],
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(
            datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
        )  # In milliseconds

        return [
            [
                base_time,
                "50000.0",  # open
                "51000.0",  # high
                "49000.0",  # low
                "50500.0",  # close
                "100.0",  # volume
                base_time + 59999,  # close time
                "5000000.0",  # quote volume
                1000,  # number of trades
                "60.0",  # taker buy base volume
                "3000000.0",  # taker buy quote volume
                "0",  # ignore
            ],
            [
                base_time + 60000,
                "50500.0",  # open
                "52000.0",  # high
                "50000.0",  # low
                "51500.0",  # close
                "150.0",  # volume
                base_time + 119999,  # close time
                "7500000.0",  # quote volume
                1500,  # number of trades
                "90.0",  # taker buy base volume
                "4500000.0",  # taker buy quote volume
                "0",  # ignore
            ],
        ]

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(
            datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
        )  # In milliseconds

        return {
            "d": {
                "t": base_time,
                "o": "50000.0",
                "h": "51000.0",
                "l": "49000.0",
                "c": "50500.0",
                "v": "100.0",
                "qv": "5000000.0",
                "n": 1000,
            }
        }

    # Additional test cases specific to MEXCSpotAdapter

    def test_custom_trading_pair_format(self, adapter):
        """Test trading pair format for various cases."""
        # Test with multiple hyphens
        assert adapter.get_trading_pair_format("BTC-USDT-PERP") == "BTC_USDT_PERP"

        # Test with lowercase
        assert adapter.get_trading_pair_format("btc-usdt") == "btc_usdt"

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
        """Test field mapping for REST response parsing."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

        # Create a mock response row
        row = [
            timestamp,  # Open time
            "50000.0",  # Open
            "51000.0",  # High
            "49000.0",  # Low
            "50500.0",  # Close
            "100.0",  # Volume
            timestamp + 59999,  # Close time
            "5000000.0",  # Quote asset volume
            1000,  # Number of trades
            "60.0",  # Taker buy base asset volume
            "3000000.0",  # Taker buy quote asset volume
            "0",  # Ignore
        ]

        candles = adapter._parse_rest_response([row])

        # Verify correct parsing
        assert len(candles) == 1
        candle = candles[0]

        # Verify field mapping
        assert candle.timestamp == int(timestamp / 1000)  # Should be in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        assert candle.n_trades == 1000
        assert candle.taker_buy_base_volume == 60.0
        assert candle.taker_buy_quote_volume == 3000000.0

    def test_parse_ws_message_field_mapping(self, adapter):
        """Test field mapping for WebSocket message parsing."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

        # Create a mock WebSocket message
        message = {
            "d": {
                "t": timestamp,
                "o": "50000.0",
                "h": "51000.0",
                "l": "49000.0",
                "c": "50500.0",
                "v": "100.0",
                "qv": "5000000.0",
                "n": 1000,
            }
        }

        candles = adapter.parse_ws_message(message)

        # Verify correct parsing
        assert candles is not None
        assert len(candles) == 1
        candle = candles[0]

        # Verify field mapping
        assert candle.timestamp == int(timestamp / 1000)  # Should be in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        assert candle.n_trades == 1000

    def test_parse_ws_message_invalid(self, adapter):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"method": "ping", "data": "some_data"}
        candles = adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = adapter.parse_ws_message(None)
        assert candles is None

    def test_timestamp_conversion(self, adapter):
        """Test timestamp conversion in MEXC format."""
        # Test timestamp conversion methods
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC

        # To exchange should convert to milliseconds
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_seconds * 1000

        # Ensure timestamp is in seconds regardless of input format
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds * 1000) == timestamp_seconds
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds) == timestamp_seconds

    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async(self, adapter, trading_pair, interval):
        """Test fetch_rest_candles async method for MEXCSpotAdapter."""
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
