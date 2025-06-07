"""
Tests for the KucoinBaseAdapter using the base adapter test class.
"""

from datetime import datetime, timezone
from unittest import mock

from candles_feed.adapters.kucoin.base_adapter import KucoinBaseAdapter
from candles_feed.adapters.kucoin.constants import (
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class ConcreteKucoinAdapter(KucoinBaseAdapter):
    """Concrete implementation of KucoinBaseAdapter for testing."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles."""
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL."""
        return SPOT_WSS_URL

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for REST API request."""
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "type": interval,
        }

        if limit is not None:
            params["limit"] = limit

        if start_time is not None:
            params["startAt"] = self.convert_timestamp_to_exchange(start_time)

        if end_time is not None:
            params["endAt"] = self.convert_timestamp_to_exchange(end_time)

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects."""
        if data is None:
            return []

        candles = []

        if isinstance(data, dict) and "data" in data:
            # KuCoin spot format
            candle_data = data.get("data", [])

            for row in candle_data:
                # Handle test fixture format which might have a different order
                if len(row) >= 7:
                    timestamp = self.ensure_timestamp_in_seconds(row[0])
                    open_price = float(row[1])
                    close = float(row[2])
                    high = float(row[3])
                    low = float(row[4])
                    volume = float(row[5])
                    quote_volume = float(row[6])

                    candles.append(
                        CandleData(
                            timestamp_raw=timestamp,
                            open=open_price,
                            high=high,
                            low=low,
                            close=close,
                            volume=volume,
                            quote_asset_volume=quote_volume,
                            n_trades=0,  # Not provided by KuCoin
                        )
                    )

        return candles

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects."""
        if data is None:
            return None

        # Check if this is a candle message from KuCoin
        if (
            isinstance(data, dict)
            and data.get("type") == "message"
            and data.get("topic", "").startswith("/market/candles:")
            and "data" in data
        ):
            candle_data = data["data"]

            if isinstance(candle_data, dict) and "candles" in candle_data:
                row = candle_data["candles"]
                if len(row) >= 7:
                    # KuCoin provides: [timestamp, open, close, high, low, volume, turnover]
                    timestamp = self.ensure_timestamp_in_seconds(row[0])
                    open_price = float(row[1])
                    close = float(row[2])
                    high = float(row[3])
                    low = float(row[4])
                    volume = float(row[5])
                    quote_volume = float(row[6])

                    return [
                        CandleData(
                            timestamp_raw=timestamp,
                            open=open_price,
                            high=high,
                            low=low,
                            close=close,
                            volume=volume,
                            quote_asset_volume=quote_volume,
                            n_trades=0,  # Not provided by KuCoin
                        )
                    ]
        return None


class TestKucoinBaseAdapter(BaseAdapterTest):
    """Test suite for the KucoinBaseAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return ConcreteKucoinAdapter()

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

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = int(
            datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
        )  # In milliseconds

        return {
            "code": "200000",
            "data": [
                [
                    str(base_time),
                    "50000.0",  # open
                    "50500.0",  # close
                    "51000.0",  # high
                    "49000.0",  # low
                    "100.0",  # volume
                    "5000000.0",  # quote volume
                ],
                [
                    str(base_time + 60000),
                    "50500.0",  # open
                    "51500.0",  # close
                    "52000.0",  # high
                    "50000.0",  # low
                    "150.0",  # volume
                    "7500000.0",  # quote volume
                ],
            ],
        }

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = int(
            datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
        )  # In milliseconds

        return {
            "type": "message",
            "topic": "/market/candles:BTC-USDT_1m",
            "subject": "trade.candles.update",
            "data": {
                "symbol": "BTC-USDT",
                "candles": [
                    str(base_time),
                    "50000.0",  # open
                    "50500.0",  # close
                    "51000.0",  # high
                    "49000.0",  # low
                    "100.0",  # volume
                    "5000000.0",  # quote volume
                ],
                "time": base_time,
            },
        }

    # Additional test cases specific to KucoinBaseAdapter

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

    def test_trading_pair_format_unchanged(self, adapter):
        """Test that trading pair format is unchanged for KuCoin."""
        # KuCoin doesn't change the format, it uses the same format as our standard
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC-USDT"
        assert adapter.get_trading_pair_format("ETH-BTC") == "ETH-BTC"
        assert adapter.get_trading_pair_format("SOL-USDT") == "SOL-USDT"

    @mock.patch("time.time")
    def test_websocket_subscription_id(self, mock_time, adapter):
        """Test that WebSocket subscription ID is based on current time."""
        fixed_time = 1622505600.0
        mock_time.return_value = fixed_time

        payload = adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        assert payload["id"] == int(fixed_time * 1000)  # Should be current time in milliseconds

    def test_parse_rest_response_field_mapping(self, adapter):
        """Test field mapping for REST response parsing."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

        # Create a mock response
        mock_response = {
            "code": "200000",
            "data": [
                [
                    str(timestamp),
                    "50000.0",  # open
                    "50500.0",  # close
                    "51000.0",  # high
                    "49000.0",  # low
                    "100.0",  # volume
                    "5000000.0",  # quote volume
                ]
            ],
        }

        candles = adapter._parse_rest_response(mock_response)

        # Verify correct parsing
        assert len(candles) == 1
        candle = candles[0]

        # Verify field mapping - note KuCoin has a different field order
        assert candle.timestamp == int(timestamp / 1000)  # Should be in seconds
        assert candle.open == 50000.0
        assert candle.close == 50500.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0

    def test_parse_ws_message_field_mapping(self, adapter):
        """Test field mapping for WebSocket message parsing."""
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

        # Create a mock WebSocket message
        message = {
            "type": "message",
            "topic": "/market/candles:BTC-USDT_1m",
            "data": {
                "candles": [
                    str(timestamp),
                    "50000.0",  # open
                    "50500.0",  # close
                    "51000.0",  # high
                    "49000.0",  # low
                    "100.0",  # volume
                    "5000000.0",  # quote volume
                ]
            },
        }

        candles = adapter.parse_ws_message(message)

        # Verify correct parsing
        assert candles is not None
        assert len(candles) == 1
        candle = candles[0]

        # Verify field mapping - note KuCoin has a different field order
        assert candle.timestamp == int(timestamp / 1000)  # Should be in seconds
        assert candle.open == 50000.0
        assert candle.close == 50500.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0

    def test_ws_supported_intervals(self, adapter):
        """Test that only 1m interval is supported for WebSocket."""
        # KuCoin only supports 1m interval for WebSocket
        ws_intervals = adapter.get_ws_supported_intervals()
        assert ws_intervals == WS_INTERVALS
        assert len(ws_intervals) == 1
        assert "1m" in ws_intervals

    # Override the BaseAdapterTest method for WebSocket supported intervals
    # KuCoin is special because it only supports 1m interval for WebSocket
    def test_get_ws_supported_intervals(self, adapter):
        """Test getting WebSocket supported intervals."""
        ws_intervals = adapter.get_ws_supported_intervals()

        # Basic validation
        assert isinstance(ws_intervals, list)

        # For KuCoin, we only expect 1m interval
        assert ws_intervals == ["1m"]
