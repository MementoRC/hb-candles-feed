"""
Tests for the CoinbaseAdvancedTradeBaseAdapter using the base adapter test class.
"""

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from candles_feed.adapters.coinbase_advanced_trade.base_adapter import (
    CoinbaseAdvancedTradeBaseAdapter,
)
from candles_feed.adapters.coinbase_advanced_trade.constants import (
    INTERVAL_TO_GRANULARITY,
    INTERVALS,
)
from tests.unit.adapters.base_adapter_test import BaseAdapterTest


# Concrete implementation of CoinbaseAdvancedTradeBaseAdapter for testing
class ConcreteCoinbaseAdvancedTradeAdapter(CoinbaseAdvancedTradeBaseAdapter):
    """Concrete implementation of CoinbaseAdvancedTradeBaseAdapter for testing."""

    @staticmethod
    def _get_rest_url() -> str:
        return "https://test.coinbase.com/api/v3/brokerage/products/{product_id}/candles"

    @staticmethod
    def _get_ws_url() -> str:
        return "wss://test.coinbase.com/ws"

    # Override _parse_rest_response to handle None properly
    def _parse_rest_response(self, data: dict | list | None) -> list:
        if data is None:
            raise ValueError("unparseable REST response")
        return super()._parse_rest_response(data)

    # Override get_supported_intervals to include needed intervals for tests
    def get_supported_intervals(self) -> dict[str, int]:
        return {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
        }


class TestCoinbaseAdvancedTradeBaseAdapter(BaseAdapterTest):
    """Test suite for the CoinbaseAdvancedTradeBaseAdapter using the base adapter test class."""

    def create_adapter(self):
        """Create an instance of the adapter to test."""
        return ConcreteCoinbaseAdvancedTradeAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter."""
        return trading_pair  # Coinbase Advanced Trade keeps the same format

    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter."""
        return "https://test.coinbase.com/api/v3/brokerage/products/{product_id}/candles"

    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter."""
        return "wss://test.coinbase.com/ws"

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

    # Additional test cases specific to CoinbaseAdvancedTradeBaseAdapter

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

    def test_ws_supported_intervals_is_5m_only(self, adapter):
        """The Coinbase candles channel is fixed at 5 minutes."""
        assert adapter.get_ws_supported_intervals() == ["5m"]
        assert "5m" in INTERVALS

    def test_get_rest_params_window_without_start(self, adapter):
        """Without a start time, start/end span the last `limit` candles ending now."""
        params = adapter._get_rest_params("BTC-USD", "5m", limit=10)

        assert params["granularity"] == "FIVE_MINUTE"
        assert int(params["end"]) - int(params["start"]) == 10 * 300
        assert params["limit"] == 10

    def test_get_rest_params_limit_capped_at_350(self, adapter):
        """The limit never exceeds Coinbase's maximum of 350."""
        params = adapter._get_rest_params("BTC-USD", "1m", limit=1000)

        assert params["limit"] == 350
        assert int(params["end"]) - int(params["start"]) == 350 * 60

    def test_get_ws_subscription_payload_has_no_granularity(self, adapter):
        """The candles channel takes no granularity."""
        payload = adapter.get_ws_subscription_payload("BTC-USD", "5m")

        assert payload == {"type": "subscribe", "channel": "candles", "product_ids": ["BTC-USD"]}

    def test_parse_ws_message_uses_each_candle_start(self, adapter):
        """Each candle is stamped with its own start, not the event timestamp."""
        message = {
            "channel": "candles",
            "timestamp": "2023-02-14T17:02:36.346Z",
            "events": [
                {
                    "type": "snapshot",
                    "candles": [
                        {
                            "start": "1676394000",
                            "high": "2",
                            "low": "1",
                            "open": "1",
                            "close": "2",
                            "volume": "3",
                            "product_id": "BTC-USD",
                        },
                        {
                            "start": "1676394300",
                            "high": "2",
                            "low": "1",
                            "open": "1",
                            "close": "2",
                            "volume": "3",
                            "product_id": "BTC-USD",
                        },
                    ],
                }
            ],
        }

        candles = adapter.parse_ws_message(message)

        assert [c.timestamp for c in candles] == [1676394000, 1676394300]

    async def test_fetch_rest_candles_async(self, adapter, trading_pair, interval):
        """Override the generic check: the URL is formatted and the params embed "now"."""
        await self.test_fetch_rest_candles_custom(adapter, trading_pair, interval)

    async def test_fetch_rest_candles_custom(self, adapter, trading_pair, interval):
        """fetch_rest_candles substitutes the product id and sends the documented params."""
        mock_client = MagicMock()
        mock_client.get_rest_data = AsyncMock(return_value=self.get_mock_candlestick_response())
        start_time = 1622505600

        candles = await adapter.fetch_rest_candles(
            trading_pair=trading_pair,
            interval=interval,
            start_time=start_time,
            network_client=mock_client,
        )

        assert len(candles) == 2
        mock_client.get_rest_data.assert_called_once()
        _, kwargs = mock_client.get_rest_data.call_args
        assert kwargs["url"] == (
            f"https://test.coinbase.com/api/v3/brokerage/products/{trading_pair}/candles"
        )
        assert "{product_id}" not in kwargs["url"]
        assert kwargs["params"] == adapter._get_rest_params(
            trading_pair, interval, start_time=start_time
        )
        assert kwargs["params"]["granularity"] == INTERVAL_TO_GRANULARITY[interval]
        assert {"start", "end"} <= kwargs["params"].keys()
