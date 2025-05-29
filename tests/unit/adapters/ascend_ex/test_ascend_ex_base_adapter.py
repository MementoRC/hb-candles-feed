"""
Tests for the AscendExBaseAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.ascend_ex.base_adapter import AscendExBaseAdapter
from candles_feed.adapters.ascend_ex.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SUB_ENDPOINT_NAME,
    WS_INTERVALS,
)
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class ConcreteAscendExAdapter(AscendExBaseAdapter):
    """Concrete implementation of AscendExBaseAdapter for testing."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles."""
        return "https://test.ascendex.com/api/pro/v1/barhist"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL."""
        return "wss://test.ascendex.com:443/api/pro/v1/websocket-for-hummingbot-liq-mining/stream"


class TestAscendExBaseAdapter(BaseAdapterTest):
    """Test suite for the AscendExBaseAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return ConcreteAscendExAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair.replace("-", "/")

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return "https://test.ascendex.com/api/pro/v1/barhist"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return "wss://test.ascendex.com:443/api/pro/v1/websocket-for-hummingbot-liq-mining/stream"

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "n": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        params = {
            "symbol": self.get_expected_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "n": limit,
            "to": end_time * 1000,  # Convert to milliseconds
        }
        # AscendEx doesn't use startTime in its API
        return params

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "op": "sub",
            "ch": f"bar:{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}:{self.get_expected_trading_pair_format(trading_pair)}",
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return {
            "status": "ok",
            "data": [
                {
                    "data": {
                        "ts": base_time,
                        "o": "50000.0",
                        "h": "51000.0",
                        "l": "49000.0",
                        "c": "50500.0",
                        "v": "5000000.0"
                    }
                },
                {
                    "data": {
                        "ts": base_time + 60000,
                        "o": "50500.0",
                        "h": "52000.0",
                        "l": "50000.0",
                        "c": "51500.0",
                        "v": "7500000.0"
                    }
                }
            ]
        }

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000

        return {
            "m": "bar",
            "data": {
                "ts": base_time,
                "o": "50000.0",
                "h": "51000.0",
                "l": "49000.0",
                "c": "50500.0",
                "v": "5000000.0"
            }
        }

    # Additional test cases specific to AscendExBaseAdapter

    def test_ascendex_timestamp_handling(self, adapter):
        """Test AscendEx-specific timestamp handling."""
        # AscendEx uses milliseconds for timestamps
        assert adapter.TIMESTAMP_UNIT == "milliseconds"

        # Test conversion
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC
        timestamp_ms = timestamp_seconds * 1000

        # Convert to exchange format (should be in milliseconds)
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_ms

        # Convert from exchange format (should be in seconds)
        assert adapter.ensure_timestamp_in_seconds(timestamp_ms) == timestamp_seconds

    def test_ascendex_rest_params_unique_format(self, adapter):
        """Test AscendEx-specific REST parameter format."""
        # AscendEx uses 'n' instead of 'limit' and 'to' instead of 'endTime'
        params = adapter._get_rest_params(
            trading_pair="BTC-USDT",
            interval="1m",
            end_time=1622592000,
            limit=100
        )

        assert "n" in params
        assert params["n"] == 100
        assert "to" in params
        assert params["to"] == 1622592000 * 1000
        assert "startTime" not in params  # AscendEx doesn't use startTime

    def test_ascendex_ws_subscription_format(self, adapter):
        """Test AscendEx-specific websocket subscription format."""
        payload = adapter.get_ws_subscription_payload("BTC-USDT", "1m")

        assert payload["op"] == "sub"
        assert payload["ch"] == f"bar:{INTERVAL_TO_EXCHANGE_FORMAT['1m']}:BTC/USDT"

    def test_parse_ws_message_ping(self, adapter):
        """Test parsing ping WebSocket message."""
        # Sample AscendEx ping message
        ws_message = {
            "m": "ping",
            "data": {
                "ts": 1672531200000  # 2023-01-01 00:00:00 UTC in milliseconds
            }
        }

        candles = adapter.parse_ws_message(ws_message)
        # Ping messages should be ignored, returning None
        assert candles is None

    def test_parse_rest_response_no_volume(self, adapter):
        """Test that AscendEx REST response parsing correctly handles volume data."""
        # AscendEx provides quote asset volume but not base asset volume
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000
        response = {
            "status": "ok",
            "data": [
                {
                    "data": {
                        "ts": base_time,
                        "o": "50000.0",
                        "h": "51000.0",
                        "l": "49000.0",
                        "c": "50500.0",
                        "v": "5000000.0"  # This is quote asset volume in AscendEx
                    }
                }
            ]
        }

        candles = adapter._parse_rest_response(response)

        assert len(candles) == 1
        assert candles[0].quote_asset_volume == 5000000.0
        assert candles[0].volume == 0.0  # Base asset volume not provided by AscendEx
