"""
Tests for the CoinbaseAdvancedTradeBaseAdapter using the base adapter test class.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

from candles_feed.adapters.coinbase_advanced_trade.base_adapter import CoinbaseAdvancedTradeBaseAdapter
from candles_feed.adapters.coinbase_advanced_trade.constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
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
            return []
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
            "granularity": INTERVALS[interval],
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter."""
        # Coinbase does not use the limit parameter
        return {
            "granularity": INTERVALS[interval],
            "start": start_time,  # Coinbase uses seconds, not milliseconds
            "end": end_time,      # Coinbase uses seconds, not milliseconds
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter."""
        return {
            "type": "subscribe",
            "product_ids": [trading_pair],
            "channel": "candles",
            "granularity": INTERVALS[interval],
        }

    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter."""
        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc).isoformat()
        
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
                    "start": (datetime(2023, 1, 1, 0, 1, tzinfo=timezone.utc)).isoformat(),
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
        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc).isoformat()
        
        return {
            "channel": "candles",
            "client_id": "test-client",
            "timestamp": datetime(2023, 1, 1, 0, 0, 1, tzinfo=timezone.utc).isoformat(),
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
        timestamp = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        
        # Create a simple object with ISO datetime string
        test_data = {"timestamp": iso_datetime}
        
        # Ensure the adapter can handle ISO datetime strings
        result = adapter.ensure_timestamp_in_seconds(test_data.get("timestamp"))
        assert result == timestamp
    
    @pytest.mark.asyncio
    @patch.object(ConcreteCoinbaseAdvancedTradeAdapter, '_get_rest_url')
    async def test_fetch_rest_candles_custom(self, mock_get_rest_url, adapter, trading_pair, interval):
        """Custom async test for fetch_rest_candles."""
        # Mock the URL to be pre-formatted with the trading pair
        formatted_url = f"https://test.coinbase.com/api/v3/brokerage/products/{trading_pair}/candles"
        mock_get_rest_url.return_value = formatted_url
        
        # Create a mock network client
        mock_client = MagicMock()
        mock_client.get_rest_data = AsyncMock()
        
        # Configure the mock to return a specific response when called
        response_data = self.get_mock_candlestick_response()
        mock_client.get_rest_data.return_value = response_data
        
        # Test the method with our mock
        candles = await adapter.fetch_rest_candles(
            trading_pair=trading_pair,
            interval=interval,
            network_client=mock_client
        )
        
        # Verify the result
        assert len(candles) == 2
        
        # Check that the mock was called with the correct parameters
        params = adapter._get_rest_params(trading_pair, interval)
        
        mock_client.get_rest_data.assert_called_once()
        args, kwargs = mock_client.get_rest_data.call_args
        assert kwargs['url'] == formatted_url
        assert kwargs['params'] == params