"""
Tests for the base adapter functionality.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData


class TestTimestampConversion:
    """Tests for the timestamp conversion methods in BaseAdapter."""

    class MockAdapter(BaseAdapter):
        """Mock adapter implementation for testing."""
        
        TIMESTAMP_UNIT = "milliseconds"
        
        def get_trading_pair_format(self, trading_pair: str) -> str:
            return trading_pair.replace("-", "/")
            
        def get_supported_intervals(self) -> dict[str, int]:
            return {"1m": 60, "1h": 3600}
            
        def get_ws_url(self) -> str:
            return "wss://test.com/ws"
            
        def get_ws_supported_intervals(self) -> list[str]:
            return ["1m", "1h"]
            
        def parse_ws_message(self, data: dict) -> list[CandleData] | None:
            return None
            
        def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
            return {}
            
        def _get_rest_url(self) -> str:
            return "https://test.com/api"
            
        def _get_rest_params(self, trading_pair: str, interval: str, start_time=None, 
                            end_time=None, limit=None) -> dict:
            return {}
            
        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
            return []

    class MockSecondsAdapter(MockAdapter):
        """Mock adapter with seconds timestamp unit."""
        TIMESTAMP_UNIT = "seconds"

    class MockMillisecondsAdapter(MockAdapter):
        """Mock adapter with milliseconds timestamp unit."""
        TIMESTAMP_UNIT = "milliseconds"

    class MockIso8601Adapter(MockAdapter):
        """Mock adapter with ISO8601 timestamp unit."""
        TIMESTAMP_UNIT = "iso8601"
        
    class MockUndefinedAdapter(MockAdapter):
        """Mock adapter with undefined timestamp unit."""
        TIMESTAMP_UNIT = ""

    def test_convert_timestamp_seconds(self):
        """Test converting timestamp to seconds."""
        adapter = self.MockSecondsAdapter()
        ts = 1620000000
        result = adapter.convert_timestamp_to_exchange(ts)
        assert result == 1620000000
        assert isinstance(result, int)

    def test_convert_timestamp_milliseconds(self):
        """Test converting timestamp to milliseconds."""
        adapter = self.MockMillisecondsAdapter()
        ts = 1620000000
        result = adapter.convert_timestamp_to_exchange(ts)
        assert result == 1620000000 * 1000
        assert isinstance(result, int)

    def test_convert_timestamp_milliseconds_with_float(self):
        """Test converting float timestamp to milliseconds."""
        adapter = self.MockMillisecondsAdapter()
        ts = 1620000000.5
        result = adapter.convert_timestamp_to_exchange(ts)
        # Allow for float result
        assert abs(result - 1620000000500) < 1

    def test_ensure_timestamp_in_seconds_iso(self):
        """Test converting ISO timestamp to seconds."""
        iso_timestamp = "2023-01-01T12:34:56Z"
        adapter = self.MockAdapter()
        result = adapter.ensure_timestamp_in_seconds(iso_timestamp)
        dt = datetime.fromisoformat("2023-01-01T12:34:56+00:00")
        expected = int(dt.timestamp())
        assert result == expected

    def test_ensure_timestamp_in_seconds_milliseconds(self):
        """Test converting milliseconds timestamp to seconds."""
        ms_timestamp = 1620000000000
        adapter = self.MockAdapter()
        result = adapter.ensure_timestamp_in_seconds(ms_timestamp)
        assert result == 1620000000

    def test_ensure_timestamp_in_seconds_microseconds(self):
        """Test converting microseconds timestamp to seconds."""
        us_timestamp = 1620000000000000
        adapter = self.MockAdapter()
        result = adapter.ensure_timestamp_in_seconds(us_timestamp)
        assert result == 1620000000

    def test_ensure_timestamp_in_seconds_nanoseconds(self):
        """Test converting nanoseconds timestamp to seconds."""
        ns_timestamp = 1620000000000000000
        adapter = self.MockAdapter()
        result = adapter.ensure_timestamp_in_seconds(ns_timestamp)
        assert result == 1620000000

    def test_ensure_timestamp_in_seconds_seconds(self):
        """Test converting seconds timestamp to seconds (no change)."""
        s_timestamp = 1620000000
        adapter = self.MockAdapter()
        result = adapter.ensure_timestamp_in_seconds(s_timestamp)
        assert result == 1620000000

    def test_ensure_timestamp_in_seconds_none(self):
        """Test handling None timestamp."""
        adapter = self.MockAdapter()
        result = adapter.ensure_timestamp_in_seconds(None)
        # Should be close to now
        now = int(datetime.now(timezone.utc).timestamp())
        assert abs(result - now) < 10


