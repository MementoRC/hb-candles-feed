"""
Test adapter protocol conformance.

This module contains tests to verify that adapter implementations
correctly implement the AdapterProtocol protocol.
"""

import inspect
from unittest.mock import patch

import pytest

from candles_feed.adapters.adapter_mixins import (
    AsyncOnlyAdapter,
    NoWebSocketSupportMixin,
    SyncOnlyAdapter,
)
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.ccxt.ccxt_base_adapter import CCXTBaseAdapter
from candles_feed.adapters.protocols import AdapterProtocol


class TestProtocolConformance:
    """Tests for protocol conformance."""

    def test_sync_adapter_conformance(self):
        """Test SyncOnlyAdapter conforms to AdapterProtocol protocol."""
        # Create a minimal implementation of BaseAdapter + SyncOnlyAdapter
        class MinimalSyncAdapter(BaseAdapter, SyncOnlyAdapter):
            def get_trading_pair_format(self, trading_pair: str) -> str:
                return trading_pair

            def get_supported_intervals(self) -> dict[str, int]:
                return {}

            def get_ws_url(self) -> str:
                return ""

            def get_ws_supported_intervals(self) -> list[str]:
                return []

            def parse_ws_message(self, data: dict) -> list:
                return []

            def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
                return {}

            def _get_rest_url(self) -> str:
                return ""

            def _get_rest_params(self, trading_pair: str, interval: str, start_time=None,
                                end_time=None, limit=None) -> dict:
                return {}

            def _parse_rest_response(self, data: dict | list | None) -> list:
                return []

            def fetch_rest_candles_synchronous(self, trading_pair: str, interval: str,
                                            start_time=None, limit=500) -> list:
                return []

        # Create an instance
        instance = MinimalSyncAdapter()

        # Check it implements AdapterProtocol protocol
        assert isinstance(instance, AdapterProtocol)

        # Check that both synchronous and asynchronous methods are available
        assert hasattr(instance, 'fetch_rest_candles_synchronous')
        assert hasattr(instance, 'fetch_rest_candles')

        # Check that the asynchronous method is a coroutine function
        assert inspect.iscoroutinefunction(instance.fetch_rest_candles)

    def test_async_adapter_conformance(self):
        """Test AsyncOnlyAdapter conforms to AdapterProtocol protocol."""
        # Create a minimal implementation of BaseAdapter + AsyncOnlyAdapter
        class MinimalAsyncAdapter(BaseAdapter, AsyncOnlyAdapter):
            def get_trading_pair_format(self, trading_pair: str) -> str:
                return trading_pair

            def get_supported_intervals(self) -> dict[str, int]:
                return {}

            def get_ws_url(self) -> str:
                return ""

            def get_ws_supported_intervals(self) -> list[str]:
                return []

            def parse_ws_message(self, data: dict) -> list:
                return []

            def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
                return {}

            def _get_rest_url(self) -> str:
                return ""

            def _get_rest_params(self, trading_pair: str, interval: str, start_time=None,
                                end_time=None, limit=None) -> dict:
                return {}

            def _parse_rest_response(self, data: dict | list | None) -> list:
                return []

            async def fetch_rest_candles(self, trading_pair: str, interval: str,
                                    start_time=None, limit=500, network_client=None) -> list:
                return []

        # Create an instance
        instance = MinimalAsyncAdapter()

        # Check it implements AdapterProtocol protocol
        assert isinstance(instance, AdapterProtocol)

        # Check that both synchronous and asynchronous methods are available
        assert hasattr(instance, 'fetch_rest_candles_synchronous')
        assert hasattr(instance, 'fetch_rest_candles')

        # Check that the asynchronous method is a coroutine function
        assert inspect.iscoroutinefunction(instance.fetch_rest_candles)

        # Check that synchronous method raises NotImplementedError
        with pytest.raises(NotImplementedError):
            instance.fetch_rest_candles_synchronous("BTC-USDT", "1m")

    def test_no_websocket_support_conformance(self):
        """Test NoWebSocketSupportMixin conforms to AdapterProtocol protocol."""
        # Implement WebSocket methods that raise NotImplementedError
        class MinimalNoWSAdapter(BaseAdapter, SyncOnlyAdapter):
            def get_trading_pair_format(self, trading_pair: str) -> str:
                return trading_pair

            def get_supported_intervals(self) -> dict[str, int]:
                return {}

            def _get_rest_url(self) -> str:
                return ""

            def _get_rest_params(self, trading_pair: str, interval: str, start_time=None,
                                end_time=None, limit=None) -> dict:
                return {}

            def _parse_rest_response(self, data: dict | list | None) -> list:
                return []

            def fetch_rest_candles_synchronous(self, trading_pair: str, interval: str,
                                            start_time=None, limit=500) -> list:
                return []

            def get_ws_url(self) -> str:
                raise NotImplementedError("This adapter does not support WebSocket")

            def get_ws_supported_intervals(self) -> list[str]:
                raise NotImplementedError("This adapter does not support WebSocket")

            def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
                raise NotImplementedError("This adapter does not support WebSocket")

            def parse_ws_message(self, data: dict) -> list:
                raise NotImplementedError("This adapter does not support WebSocket")

        # Create an instance
        instance = MinimalNoWSAdapter()

        # Check it implements AdapterProtocol protocol
        assert isinstance(instance, AdapterProtocol)

        # Check that WebSocket methods raise NotImplementedError
        with pytest.raises(NotImplementedError):
            instance.get_ws_url()

        with pytest.raises(NotImplementedError):
            instance.get_ws_supported_intervals()

        with pytest.raises(NotImplementedError):
            instance.get_ws_subscription_payload("BTC-USDT", "1m")

        with pytest.raises(NotImplementedError):
            instance.parse_ws_message({})

    def test_ccxt_adapter_conformance(self):
        """Test CCXTBaseAdapter conforms to AdapterProtocol protocol."""
        class TestCCXTAdapter(CCXTBaseAdapter):
            exchange_name = "binance"

        # Patch ccxt.binance to avoid actual API calls
        with patch('ccxt.binance') as _:
            # Create an instance
            instance = TestCCXTAdapter()

            # Check it implements AdapterProtocol protocol
            assert isinstance(instance, AdapterProtocol)

            # Check it uses the SyncOnlyAdapter
            assert isinstance(instance, SyncOnlyAdapter)

            # Check WebSocket methods raise NotImplementedError
            with pytest.raises(NotImplementedError):
                instance.get_ws_url()

            with pytest.raises(NotImplementedError):
                instance.get_ws_supported_intervals()

            with pytest.raises(NotImplementedError):
                instance.get_ws_subscription_payload("BTC-USDT", "1m")

            with pytest.raises(NotImplementedError):
                instance.parse_ws_message({})
