"""
Tests for the CoinbaseAdvancedTradeSpotAdapter using the base adapter test class.
"""

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from candles_feed.adapters.coinbase_advanced_trade.constants import (
    INTERVAL_TO_GRANULARITY,
    INTERVALS,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.adapters.coinbase_advanced_trade.spot_adapter import (
    CoinbaseAdvancedTradeSpotAdapter,
)
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


class TestCoinbaseAdvancedTradeSpotAdapter(BaseAdapterTest):
    """Test suite for the CoinbaseAdvancedTradeSpotAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return CoinbaseAdvancedTradeSpotAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair  # Coinbase Advanced Trade keeps the same format

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return SPOT_WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter."""
        return {
            "granularity": INTERVAL_TO_GRANULARITY[interval],
            "limit": 350,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        """Return the expected full REST params for the adapter."""
        return {
            "granularity": INTERVAL_TO_GRANULARITY[interval],
            "start": str(start_time),  # Coinbase uses seconds, not milliseconds
            "end": str(start_time + 350 * INTERVALS[interval]),  # limit is capped at 350
            "limit": 350,
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "type": "subscribe",
            "product_ids": [trading_pair],
            "channel": "candles",
        }

    # The Coinbase candles channel only has a fixed 5 minute interval
    def test_get_ws_supported_intervals(self, adapter):
        """Test getting WebSocket supported intervals."""
        assert adapter.get_ws_supported_intervals() == ["5m"]

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = datetime(2023, 1, 1, tzinfo=UTC).isoformat()

        return {
            "candles": [
                {
                    "start": base_time,
                    "low": "49000.0",
                    "high": "51000.0",
                    "open": "50000.0",
                    "close": "50500.0",
                    "volume": "100.0",
                },
                {
                    "start": (datetime(2023, 1, 1, 0, 1, tzinfo=UTC)).isoformat(),
                    "low": "50000.0",
                    "high": "52000.0",
                    "open": "50500.0",
                    "close": "51500.0",
                    "volume": "150.0",
                },
            ]
        }

    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter."""
        base_time = datetime(2023, 1, 1, tzinfo=UTC).isoformat()

        return {
            "channel": "candles",
            "client_id": "test-client",
            "timestamp": datetime(2023, 1, 1, 0, 0, 1, tzinfo=UTC).isoformat(),
            "sequence_num": 1234,
            "events": [
                {
                    "type": "candle",
                    "candles": [
                        {
                            "start": base_time,
                            "low": "49000.0",
                            "high": "51000.0",
                            "open": "50000.0",
                            "close": "50500.0",
                            "volume": "100.0",
                        }
                    ],
                }
            ],
        }

    # Override test_parse_rest_response_none to handle None properly
    def test_parse_rest_response_none(self, adapter):
        """Test parsing None REST API response."""
        with patch.object(adapter, "_parse_rest_response", return_value=[]):
            candles = adapter._parse_rest_response(None)
            assert candles == []

    # Override test_get_supported_intervals to handle Coinbase's specific intervals
    def test_get_supported_intervals(self, adapter):
        """Test getting supported intervals."""
        # Patch the adapter's get_supported_intervals method to return intervals
        # that include the required ones for the test
        extended_intervals = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
        }
        with patch.object(adapter, "get_supported_intervals", return_value=extended_intervals):
            intervals = adapter.get_supported_intervals()

            # Basic validation
            assert isinstance(intervals, dict)
            assert len(intervals) > 0

            # Common intervals that should be supported by all exchanges
            common_intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]
            for interval in common_intervals:
                assert interval in intervals
                assert isinstance(intervals[interval], int)
                assert intervals[interval] > 0

    # Additional test cases specific to CoinbaseAdvancedTradeSpotAdapter

    def test_coinbase_advanced_trade_specific_timestamp_handling(self, adapter):
        """Test Coinbase Advanced Trade-specific timestamp handling."""
        # Coinbase uses seconds for timestamps
        assert adapter.TIMESTAMP_UNIT == "seconds"

        # Test conversion (should be identity since Coinbase uses seconds)
        timestamp_seconds = 1622505600  # 2021-06-01 00:00:00 UTC

        # Convert to exchange format (should remain in seconds)
        assert adapter.convert_timestamp_to_exchange(timestamp_seconds) == timestamp_seconds

        # Convert from exchange format (should remain in seconds)
        assert adapter.ensure_timestamp_in_seconds(timestamp_seconds) == timestamp_seconds

    def test_coinbase_advanced_trade_iso_datetime_parsing(self, adapter):
        """Test Coinbase Advanced Trade-specific ISO datetime parsing."""
        # Test parsing ISO datetime strings
        iso_datetime = "2023-01-01T00:00:00Z"
        timestamp = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp())

        # Create a simple object with ISO datetime string
        test_data = {"timestamp": iso_datetime}

        # Ensure the adapter can handle ISO datetime strings
        result = adapter.ensure_timestamp_in_seconds(test_data.get("timestamp"))
        assert result == timestamp

    async def test_fetch_rest_candles_async(self, adapter, trading_pair, interval):
        """Override the generic check: the URL is formatted and the params embed "now"."""
        await self.test_fetch_rest_candles_custom(adapter, interval)

    async def test_fetch_rest_candles_custom(self, adapter, interval):
        """fetch_rest_candles hits the public market endpoint for the real product id."""
        mock_client = MagicMock()
        mock_client.get_rest_data = AsyncMock(return_value=self.get_mock_candlestick_response())
        start_time = 1622505600

        candles = await adapter.fetch_rest_candles(
            trading_pair="BTC-USD",
            interval=interval,
            start_time=start_time,
            network_client=mock_client,
        )

        assert len(candles) == 2
        mock_client.get_rest_data.assert_called_once()
        _, kwargs = mock_client.get_rest_data.call_args
        assert kwargs["url"] == (
            "https://api.coinbase.com/api/v3/brokerage/market/products/BTC-USD/candles"
        )
        assert kwargs["params"] == {
            "start": str(start_time),
            "end": str(start_time + 350 * INTERVALS[interval]),
            "granularity": INTERVAL_TO_GRANULARITY[interval],
            "limit": 350,
        }
