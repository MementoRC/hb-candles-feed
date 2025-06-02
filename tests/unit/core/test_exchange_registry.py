"""
Unit tests for the ExchangeRegistry class.
"""

from unittest.mock import MagicMock

import pytest

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


class TestExchangeRegistry:
    """Test suite for the ExchangeRegistry class."""

    def test_register_and_get_adapter_class(self):
        """Test registering and retrieving adapter classes."""
        # Clear the registry before test
        ExchangeRegistry._registry = {}

        # Create a test adapter class
        class TestAdapter(BaseAdapter):
            def get_trading_pair_format(self, trading_pair):
                return trading_pair

            def _get_rest_url(self):
                return "https://test.com/api"

            def get_ws_url(self):
                return "wss://test.com/ws"

            def _get_rest_params(
                self, trading_pair, interval, start_time=None, end_time=None, limit=None
            ):
                return {"symbol": trading_pair, "interval": interval}

            def _parse_rest_response(self, data):
                return []

            def get_ws_subscription_payload(self, trading_pair, interval):
                return {"subscribe": trading_pair}

            def parse_ws_message(self, data):
                return None

            def get_supported_intervals(self):
                return {"1m": 60}

            def get_ws_supported_intervals(self):
                return ["1m"]

        # Register the adapter
        ExchangeRegistry.register("test_exchange")(TestAdapter)

        # Verify it was registered properly
        assert "test_exchange" in ExchangeRegistry._registry
        assert ExchangeRegistry._registry["test_exchange"] == TestAdapter

        # Get the adapter class by name
        retrieved_class = ExchangeRegistry.get_adapter_class("test_exchange")
        assert retrieved_class == TestAdapter

    def test_get_registered_exchanges(self):
        """Test getting a list of registered exchange names."""
        # Clear the registry
        ExchangeRegistry._registry = {}

        # Create mock adapter classes
        mock_adapter_1 = MagicMock()
        mock_adapter_2 = MagicMock()

        # Register the adapters
        ExchangeRegistry._registry = {"exchange1": mock_adapter_1, "exchange2": mock_adapter_2}

        # Get the list of exchanges
        exchanges = ExchangeRegistry.get_registered_exchanges()

        # Verify the list
        assert len(exchanges) == 2
        assert "exchange1" in exchanges
        assert "exchange2" in exchanges

    def test_get_adapter_instance(self):
        """Test getting an adapter instance."""
        # Clear the registry
        ExchangeRegistry._registry = {}

        # Create a test adapter class
        class TestAdapter(BaseAdapter):
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

            def get_trading_pair_format(self, trading_pair):
                return trading_pair

            def _get_rest_url(self):
                return "https://test.com/api"

            def get_ws_url(self):
                return "wss://test.com/ws"

            def _get_rest_params(
                self, trading_pair, interval, start_time=None, end_time=None, limit=None
            ):
                return {"symbol": trading_pair, "interval": interval}

            def _parse_rest_response(self, data):
                return []

            def get_ws_subscription_payload(self, trading_pair, interval):
                return {"subscribe": trading_pair}

            def parse_ws_message(self, data):
                return None

            def get_supported_intervals(self):
                return {"1m": 60}

            def get_ws_supported_intervals(self):
                return ["1m"]

        # Register the adapter
        ExchangeRegistry.register("test_exchange")(TestAdapter)

        # Get an instance with custom arguments
        instance = ExchangeRegistry.get_adapter_instance("test_exchange", "arg1", kwarg1="value1")

        # Verify the instance
        assert isinstance(instance, TestAdapter)
        assert instance.args == ("arg1",)
        assert instance.kwargs == {"kwarg1": "value1"}

    def test_get_nonexistent_adapter(self):
        """Test attempting to get a non-existent adapter."""
        # Clear the registry
        ExchangeRegistry._registry = {}

        # Try to get a non-existent adapter
        with pytest.raises(ValueError) as excinfo:
            ExchangeRegistry.get_adapter_class("nonexistent_exchange")

        assert "Adapter not found for exchange: nonexistent_exchange" in str(excinfo.value)

        # Try to get an instance of a non-existent adapter
        with pytest.raises(ValueError) as excinfo:
            ExchangeRegistry.get_adapter_instance("nonexistent_exchange")

        assert "Adapter not found for exchange: nonexistent_exchange" in str(excinfo.value)
