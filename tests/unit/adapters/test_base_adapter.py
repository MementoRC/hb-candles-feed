"""
Tests for the base adapter functionality.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol


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

        def _get_rest_params(
            self, trading_pair: str, interval: str, start_time=None, end_time=None, limit=None
        ) -> dict:
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

    def test_convert_timestamp_iso8601(self):
        """Test converting timestamp to ISO8601 format."""
        adapter = self.MockIso8601Adapter()
        ts = 1620000000
        result = adapter.convert_timestamp_to_exchange(ts)
        assert isinstance(result, str)
        assert "T" in result
        assert "Z" in result
        # Convert back and verify
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert int(dt.timestamp()) == ts

    def test_convert_timestamp_undefined_unit(self):
        """Test converting timestamp with undefined timestamp unit."""
        adapter = self.MockUndefinedAdapter()
        ts = 1620000000
        with pytest.raises(NotImplementedError):
            adapter.convert_timestamp_to_exchange(ts)


class TestBaseAdapter:
    """Tests for the BaseAdapter class functionality."""

    class ConcreteAdapter(BaseAdapter):
        """Concrete implementation of BaseAdapter for testing."""

        TIMESTAMP_UNIT = "seconds"

        def __init__(self):
            self.fetch_rest_candles_calls = []

        @staticmethod
        def get_trading_pair_format(trading_pair: str) -> str:
            """Convert trading pair to exchange format."""
            return trading_pair.replace("-", "/")

        def get_supported_intervals(self) -> dict[str, int]:
            """Get supported intervals."""
            return {"1m": 60, "1h": 3600, "1d": 86400}

        def get_ws_url(self) -> str:
            """Get WebSocket URL."""
            return "wss://test.com/ws"

        def get_ws_supported_intervals(self) -> list[str]:
            """Get WebSocket supported intervals."""
            return ["1m", "1h", "1d"]

        def parse_ws_message(self, data: dict) -> list[CandleData] | None:
            """Parse WebSocket message."""
            if not isinstance(data, dict) or data.get("type") != "candle":
                return None

            return [
                CandleData(
                    timestamp_raw=data["data"]["timestamp"],
                    open=data["data"]["open"],
                    high=data["data"]["high"],
                    low=data["data"]["low"],
                    close=data["data"]["close"],
                    volume=data["data"]["volume"],
                )
            ]

        def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
            """Get WebSocket subscription payload."""
            return {"subscribe": f"{trading_pair.lower()}@kline_{interval}"}

        def _get_rest_url(self) -> str:
            """Get REST URL."""
            return "https://test.com/api"

        def _get_rest_params(
            self, trading_pair: str, interval: str, start_time=None, end_time=None, limit=None
        ) -> dict:
            """Get REST parameters."""
            params = {"symbol": trading_pair, "interval": interval}
            if start_time:
                params["startTime"] = self.convert_timestamp_to_exchange(start_time)
            if end_time:
                params["endTime"] = self.convert_timestamp_to_exchange(end_time)
            if limit:
                params["limit"] = limit
            return params

        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
            """Parse REST response."""
            if data is None:
                return []

            if isinstance(data, list):
                return [
                    CandleData(
                        timestamp_raw=item[0],
                        open=float(item[1]),
                        high=float(item[2]),
                        low=float(item[3]),
                        close=float(item[4]),
                        volume=float(item[5]),
                    )
                    for item in data
                ]
            return []

        async def fetch_rest_candles(
            self,
            trading_pair: str,
            interval: str,
            start_time: int | None = None,
            limit: int = 500,
            network_client: NetworkClientProtocol | None = None,
        ) -> list[CandleData]:
            """Fetch REST candles."""
            self.fetch_rest_candles_calls.append(
                {
                    "trading_pair": trading_pair,
                    "interval": interval,
                    "start_time": start_time,
                    "limit": limit,
                    "network_client": network_client,
                }
            )

            # Default implementation for testing
            url = self._get_rest_url()
            params = self._get_rest_params(trading_pair, interval, start_time, None, limit)

            if network_client:
                response = await network_client.get_rest_data(url, params)
            else:
                # Mock response for testing
                response = [
                    [1620000000, "100.0", "101.0", "99.0", "100.5", "1000.0"],
                    [1620003600, "100.5", "102.0", "100.0", "101.5", "1500.0"],
                ]

            return self._parse_rest_response(response)

    def test_trading_pair_format(self):
        """Test trading pair format conversion."""
        adapter = self.ConcreteAdapter()
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC/USDT"

    def test_supported_intervals(self):
        """Test supported intervals retrieval."""
        adapter = self.ConcreteAdapter()
        intervals = adapter.get_supported_intervals()
        assert "1m" in intervals
        assert intervals["1m"] == 60
        assert "1h" in intervals
        assert intervals["1h"] == 3600
        assert "1d" in intervals
        assert intervals["1d"] == 86400

    def test_ws_url(self):
        """Test WebSocket URL retrieval."""
        adapter = self.ConcreteAdapter()
        assert adapter.get_ws_url() == "wss://test.com/ws"

    def test_ws_supported_intervals(self):
        """Test WebSocket supported intervals retrieval."""
        adapter = self.ConcreteAdapter()
        intervals = adapter.get_ws_supported_intervals()
        assert "1m" in intervals
        assert "1h" in intervals
        assert "1d" in intervals

    def test_parse_ws_message_valid(self):
        """Test parsing valid WebSocket message."""
        adapter = self.ConcreteAdapter()
        message = {
            "type": "candle",
            "data": {
                "timestamp": 1620000000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000.0,
            },
        }
        candles = adapter.parse_ws_message(message)
        assert len(candles) == 1
        assert candles[0].timestamp == 1620000000
        assert candles[0].open == 100.0
        assert candles[0].high == 101.0
        assert candles[0].low == 99.0
        assert candles[0].close == 100.5
        assert candles[0].volume == 1000.0

    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        adapter = self.ConcreteAdapter()
        # Not a candle message
        message = {"type": "trade", "data": {}}
        candles = adapter.parse_ws_message(message)
        assert candles is None

        # Not a dict
        message = ["not", "a", "dict"]
        candles = adapter.parse_ws_message(message)
        assert candles is None

        # None
        candles = adapter.parse_ws_message(None)
        assert candles is None

    def test_ws_subscription_payload(self):
        """Test WebSocket subscription payload."""
        adapter = self.ConcreteAdapter()
        payload = adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        assert payload["subscribe"] == "btc-usdt@kline_1m"

    def test_rest_url(self):
        """Test REST URL retrieval."""
        adapter = self.ConcreteAdapter()
        assert adapter._get_rest_url() == "https://test.com/api"

    def test_rest_params_minimal(self):
        """Test minimal REST parameters."""
        adapter = self.ConcreteAdapter()
        params = adapter._get_rest_params("BTC-USDT", "1m")
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert "startTime" not in params
        assert "endTime" not in params
        assert "limit" not in params

    def test_rest_params_full(self):
        """Test full REST parameters."""
        adapter = self.ConcreteAdapter()
        params = adapter._get_rest_params(
            "BTC-USDT", "1m", start_time=1620000000, end_time=1620100000, limit=100
        )
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert params["startTime"] == 1620000000
        assert params["endTime"] == 1620100000
        assert params["limit"] == 100

    def test_parse_rest_response_valid(self):
        """Test parsing valid REST response."""
        adapter = self.ConcreteAdapter()
        data = [
            [1620000000, "100.0", "101.0", "99.0", "100.5", "1000.0"],
            [1620003600, "100.5", "102.0", "100.0", "101.5", "1500.0"],
        ]
        candles = adapter._parse_rest_response(data)
        assert len(candles) == 2
        assert candles[0].timestamp == 1620000000
        assert candles[0].open == 100.0
        assert candles[0].close == 100.5
        assert candles[1].timestamp == 1620003600
        assert candles[1].high == 102.0
        assert candles[1].volume == 1500.0

    def test_parse_rest_response_none(self):
        """Test parsing None REST response."""
        adapter = self.ConcreteAdapter()
        candles = adapter._parse_rest_response(None)
        assert candles == []

    def test_parse_rest_response_invalid(self):
        """Test parsing invalid REST response."""
        adapter = self.ConcreteAdapter()
        candles = adapter._parse_rest_response({"not": "a list"})
        assert candles == []

    @pytest.mark.asyncio
    async def test_fetch_rest_candles(self):
        """Test fetching REST candles."""
        adapter = self.ConcreteAdapter()

        # Test with default implementation
        candles = await adapter.fetch_rest_candles("BTC-USDT", "1m")
        assert len(candles) == 2
        assert candles[0].timestamp == 1620000000
        assert candles[1].timestamp == 1620003600

        # Verify method was called with correct parameters
        assert len(adapter.fetch_rest_candles_calls) == 1
        call = adapter.fetch_rest_candles_calls[0]
        assert call["trading_pair"] == "BTC-USDT"
        assert call["interval"] == "1m"
        assert call["limit"] == 500
        assert call["network_client"] is None

    @pytest.mark.asyncio
    async def test_fetch_rest_candles_with_network_client(self):
        """Test fetching REST candles with network client."""
        adapter = self.ConcreteAdapter()

        # Create mock network client
        mock_client = Mock(spec=NetworkClientProtocol)
        mock_client.get_rest_data = AsyncMock(
            return_value=[[1620000000, "200.0", "201.0", "199.0", "200.5", "2000.0"]]
        )

        # Test with network client
        candles = await adapter.fetch_rest_candles(
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=1620000000,
            limit=100,
            network_client=mock_client,
        )

        # Verify method was called with correct parameters
        assert len(adapter.fetch_rest_candles_calls) == 1
        call = adapter.fetch_rest_candles_calls[0]
        assert call["trading_pair"] == "BTC-USDT"
        assert call["interval"] == "1m"
        assert call["start_time"] == 1620000000
        assert call["limit"] == 100
        assert call["network_client"] is mock_client

        # Verify network client was called with correct URL and params
        mock_client.get_rest_data.assert_called_once()
        url, params = mock_client.get_rest_data.call_args[0]
        assert url == "https://test.com/api"
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert params["startTime"] == 1620000000
        assert params["limit"] == 100

        # Verify parse_rest_response was called with the response
        assert len(candles) == 1
        assert candles[0].timestamp == 1620000000
        assert candles[0].open == 200.0
