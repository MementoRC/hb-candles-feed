"""
Base test class for adapter implementations.

This module provides a base test class that can be used to test any adapter
implementation in a consistent way.
"""

import abc
import contextlib
from unittest import mock

import pytest

from candles_feed.core.candle_data import CandleData


class BaseAdapterTest(abc.ABC):
    """Base test class for adapter implementations.

    This class provides common test cases for adapter implementations.
    Concrete adapter test classes should inherit from this class and
    implement the abstract methods to provide adapter-specific information.
    """

    @pytest.fixture
    def adapter(self):
        """Create an instance of the adapter to test.

        This method should be overridden to return an instance of the
        adapter that is being tested.
        """
        return self.create_adapter()

    @pytest.fixture
    def trading_pair(self):
        """Return a valid trading pair for the adapter."""
        return "BTC-USDT"

    @pytest.fixture
    def interval(self):
        """Return a valid interval for the adapter."""
        return "1m"

    @abc.abstractmethod
    def create_adapter(self):
        """Create an instance of the adapter to test.

        This method must be implemented by concrete adapter test classes.
        """
        pass

    @abc.abstractmethod
    def get_expected_trading_pair_format(self, trading_pair):
        """Return the expected trading pair format for the adapter.

        This method must be implemented by concrete adapter test classes.
        """
        pass

    @abc.abstractmethod
    def get_expected_rest_url(self):
        """Return the expected REST URL for the adapter.

        This method must be implemented by concrete adapter test classes.
        """
        pass

    @abc.abstractmethod
    def get_expected_ws_url(self):
        """Return the expected WebSocket URL for the adapter.

        This method must be implemented by concrete adapter test classes.
        """
        pass

    @abc.abstractmethod
    def get_expected_rest_params_minimal(self, trading_pair, interval):
        """Return the expected minimal REST params for the adapter.

        This method must be implemented by concrete adapter test classes.
        """
        pass

    @abc.abstractmethod
    def get_expected_rest_params_full(self, trading_pair, interval, start_time, end_time, limit):
        """Return the expected full REST params for the adapter.

        This method must be implemented by concrete adapter test classes.
        """
        pass

    @abc.abstractmethod
    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        """Return the expected WebSocket subscription payload for the adapter.

        This method must be implemented by concrete adapter test classes.
        """
        pass

    @abc.abstractmethod
    def get_mock_candlestick_response(self):
        """Return a mock candlestick response for the adapter.

        This method must be implemented by concrete adapter test classes.
        """
        pass

    @abc.abstractmethod
    def get_mock_websocket_message(self):
        """Return a mock WebSocket message for the adapter.

        This method must be implemented by concrete adapter test classes.
        """
        pass

    # Common test cases that apply to all adapters

    def test_trading_pair_format(self, adapter, trading_pair):
        """Test trading pair format conversion."""
        expected_format = self.get_expected_trading_pair_format(trading_pair)
        assert adapter.get_trading_pair_format(trading_pair) == expected_format

    def test_get_rest_url(self, adapter):
        """Test REST URL retrieval."""
        expected_url = self.get_expected_rest_url()
        assert adapter._get_rest_url() == expected_url

    def test_get_ws_url(self, adapter):
        """Test WebSocket URL retrieval."""
        expected_url = self.get_expected_ws_url()
        assert adapter._get_ws_url() == expected_url
        assert adapter.get_ws_url() == expected_url

    def test_get_rest_params_minimal(self, adapter, trading_pair, interval):
        """Test REST params with minimal parameters."""
        expected_params = self.get_expected_rest_params_minimal(trading_pair, interval)
        actual_params = adapter._get_rest_params(trading_pair, interval)

        for key, value in expected_params.items():
            assert key in actual_params
            assert actual_params[key] == value

    def test_get_rest_params_full(self, adapter, trading_pair, interval):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        end_time = 1622592000  # 2021-06-02 00:00:00 UTC
        limit = 500

        expected_params = self.get_expected_rest_params_full(
            trading_pair, interval, start_time, end_time, limit
        )

        actual_params = adapter._get_rest_params(
            trading_pair, interval, start_time=start_time, end_time=end_time, limit=limit
        )

        for key, value in expected_params.items():
            assert key in actual_params
            assert actual_params[key] == value

    def test_parse_rest_response(self, adapter):
        """Test parsing REST API response."""
        mock_response = self.get_mock_candlestick_response()
        candles = adapter._parse_rest_response(mock_response)

        # Basic validation
        assert isinstance(candles, list)
        assert all(isinstance(candle, CandleData) for candle in candles)
        assert len(candles) > 0

        # Further validation can be added in concrete adapter tests

    def test_parse_rest_response_none(self, adapter):
        """Test parsing None REST API response."""
        candles = adapter._parse_rest_response(None)
        assert candles == []

    def test_get_ws_subscription_payload(self, adapter, trading_pair, interval):
        """Test WebSocket subscription payload generation."""
        expected_payload = self.get_expected_ws_subscription_payload(trading_pair, interval)
        actual_payload = adapter.get_ws_subscription_payload(trading_pair, interval)

        assert isinstance(actual_payload, dict)

        # Compare key parts of the payload (structure may vary by exchange)
        for key, value in expected_payload.items():
            assert key in actual_payload
            assert actual_payload[key] == value

    def test_parse_ws_message_valid(self, adapter):
        """Test parsing valid WebSocket message."""
        mock_message = self.get_mock_websocket_message()
        candles = adapter.parse_ws_message(mock_message)

        # Basic validation
        assert candles is not None
        assert isinstance(candles, list)
        assert all(isinstance(candle, CandleData) for candle in candles)
        assert len(candles) > 0

        # Further validation can be added in concrete adapter tests

    def test_parse_ws_message_invalid(self, adapter):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        invalid_message = {"type": "invalid", "data": "some_data"}
        candles = adapter.parse_ws_message(invalid_message)
        assert candles is None

        # Test with None
        candles = adapter.parse_ws_message(None)
        assert candles is None

    def test_get_supported_intervals(self, adapter):
        """Test getting supported intervals."""
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

    def test_get_ws_supported_intervals(self, adapter):
        """Test getting WebSocket supported intervals."""
        ws_intervals = adapter.get_ws_supported_intervals()

        # Basic validation
        assert isinstance(ws_intervals, list)

        # Should contain at least some common intervals
        common_intervals = ["1m", "1h"]
        for interval in common_intervals:
            assert interval in ws_intervals

    def test_fetch_rest_candles_synchronous(self, adapter, trading_pair, interval):
        """Test fetch_rest_candles_synchronous (for SyncOnlyAdapter adapters)."""
        # Skip test for AsyncOnlyAdapter adapters
        with contextlib.suppress(ImportError):
            from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter

            if isinstance(adapter, AsyncOnlyAdapter):
                pytest.skip("Test only applicable for synchronous adapters")
        # Mock requests.get to avoid actual API calls
        with mock.patch("requests.get") as mock_get:
            mock_response = mock.MagicMock()
            mock_response.json.return_value = self.get_mock_candlestick_response()
            mock_get.return_value = mock_response

            candles = adapter.fetch_rest_candles_synchronous(trading_pair, interval)

            # Basic validation
            assert isinstance(candles, list)
            assert all(isinstance(candle, CandleData) for candle in candles)
            assert len(candles) > 0

            # Verify request was made correctly
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert args[0] == adapter._get_rest_url()

    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async(self, adapter, trading_pair, interval):
        """Test fetch_rest_candles async method (for AsyncOnlyAdapter adapters)."""
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
        # Verify params match expected values
        expected_params = adapter._get_rest_params(trading_pair, interval)
        assert kwargs["params"] == expected_params

    def test_error_handling_in_fetch_rest_candles(self, adapter, trading_pair, interval):
        """Test error handling in fetch_rest_candles_synchronous."""
        # Import here to avoid circular dependencies or issues if mixins are not always available
        from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter

        if isinstance(adapter, AsyncOnlyAdapter):
            # For AsyncOnlyAdapter, expect NotImplementedError
            with pytest.raises(NotImplementedError):
                adapter.fetch_rest_candles_synchronous(trading_pair, interval)
        else:
            # For other adapters, test the original HTTP error handling
            # Mock requests.get to simulate errors
            with mock.patch("requests.get") as mock_get:
                # Test HTTP error
                mock_response = mock.MagicMock()
                mock_response.raise_for_status.side_effect = Exception("HTTP Error")
                mock_get.return_value = mock_response

                # Should raise the error since we're not handling it in the adapter
                with pytest.raises(Exception, match="HTTP Error"):
                    adapter.fetch_rest_candles_synchronous(trading_pair, interval)

    def test_timestamp_conversion(self, adapter):
        """Test timestamp conversion methods."""
        # Test conversion to exchange format
        test_timestamp = 1622505600  # 2021-06-01 00:00:00 UTC

        # Should handle the adapter's timestamp unit correctly
        converted = adapter.convert_timestamp_to_exchange(test_timestamp)

        # The specific value depends on the adapter's TIMESTAMP_UNIT
        if adapter.TIMESTAMP_UNIT == "seconds":
            assert converted == test_timestamp
        elif adapter.TIMESTAMP_UNIT == "milliseconds":
            assert converted == test_timestamp * 1000

        # Test conversion from exchange format
        # Test milliseconds
        assert adapter.ensure_timestamp_in_seconds(test_timestamp * 1000) == test_timestamp
        # Test seconds
        assert adapter.ensure_timestamp_in_seconds(test_timestamp) == test_timestamp
