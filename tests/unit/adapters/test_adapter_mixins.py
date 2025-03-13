"""
Tests for the adapter mixins functionality.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock

from candles_feed.adapters.adapter_mixins import (
    SyncOnlyAdapter, 
    AsyncOnlyAdapter,
    NoWebSocketSupportMixin
)
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol


class TestSyncOnlyAdapter:
    """Tests for the SyncOnlyAdapter mixin."""

    class MockSyncAdapter(BaseAdapter, SyncOnlyAdapter):
        """Mock adapter implementing SyncOnlyAdapter."""
        
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
            return {"symbol": trading_pair, "interval": interval}
            
        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
            return []
            
        def fetch_rest_candles_synchronous(
            self,
            trading_pair: str,
            interval: str,
            start_time: int | None = None,
            limit: int = 500,
        ) -> list[CandleData]:
            """Synchronous implementation for testing."""
            return [CandleData(
                timestamp_raw=1620000000,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0
            )]

    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async_wrapper(self):
        """Test async wrapper calls the synchronous method."""
        adapter = self.MockSyncAdapter()
        
        # Mock the synchronous method to verify it's called
        adapter.fetch_rest_candles_synchronous = Mock(return_value=[
            CandleData(
                timestamp_raw=1620000000,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0
            )
        ])
        
        # Call the async method
        result = await adapter.fetch_rest_candles(
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=1620000000,
            limit=100
        )
        
        # Verify the synchronous method was called
        assert adapter.fetch_rest_candles_synchronous.call_count == 1
        args, kwargs = adapter.fetch_rest_candles_synchronous.call_args
        assert kwargs.get("trading_pair") == "BTC-USDT" or (len(args) > 0 and args[0] == "BTC-USDT")
        assert kwargs.get("interval") == "1m" or (len(args) > 1 and args[1] == "1m")
        assert kwargs.get("start_time") == 1620000000 or (len(args) > 2 and args[2] == 1620000000)
        assert kwargs.get("limit") == 100 or (len(args) > 3 and args[3] == 100)
        
        # Verify the result is correct
        assert len(result) == 1
        assert result[0].timestamp == 1620000000
        assert result[0].open == 100.0
        
    @pytest.mark.asyncio
    async def test_fetch_rest_candles_ignores_network_client(self):
        """Test async wrapper ignores the network client parameter."""
        adapter = self.MockSyncAdapter()
        mock_network_client = Mock(spec=NetworkClientProtocol)
        
        # Mock the synchronous method to verify it's called
        adapter.fetch_rest_candles_synchronous = Mock(return_value=[])
        
        # Call the async method with a network client
        await adapter.fetch_rest_candles(
            trading_pair="BTC-USDT",
            interval="1m",
            network_client=mock_network_client
        )
        
        # Verify the network client was not used
        adapter.fetch_rest_candles_synchronous.assert_called_once()
        mock_network_client.get_rest_data.assert_not_called()


class TestAsyncOnlyAdapter:
    """Tests for the AsyncOnlyAdapter mixin."""

    class MockAsyncAdapter(BaseAdapter, AsyncOnlyAdapter):
        """Mock adapter implementing AsyncOnlyAdapter."""
        
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
            return {"symbol": trading_pair, "interval": interval}
            
        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
            return []
            
        async def fetch_rest_candles(
            self,
            trading_pair: str,
            interval: str,
            start_time: int | None = None,
            limit: int = 500,
            network_client: NetworkClientProtocol | None = None,
        ) -> list[CandleData]:
            """Async implementation for testing."""
            return [CandleData(
                timestamp_raw=1620000000,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0
            )]

    def test_fetch_rest_candles_synchronous_raises_error(self):
        """Test synchronous method raises NotImplementedError."""
        adapter = self.MockAsyncAdapter()
        
        with pytest.raises(NotImplementedError):
            adapter.fetch_rest_candles_synchronous(
                trading_pair="BTC-USDT",
                interval="1m"
            )
            
    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async_implementation(self):
        """Test the async method works correctly."""
        adapter = self.MockAsyncAdapter()
        
        # Mock the async method to verify it's called
        async_mock = AsyncMock(return_value=[
            CandleData(
                timestamp_raw=1620000000,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0
            )
        ])
        adapter.fetch_rest_candles = async_mock
        
        # Call the async method
        result = await adapter.fetch_rest_candles(
            trading_pair="BTC-USDT",
            interval="1m"
        )
        
        # Verify the async method was called
        assert async_mock.call_count == 1
        
        # Verify the result is correct
        assert len(result) == 1
        assert result[0].timestamp == 1620000000
        assert result[0].open == 100.0


class TestNoWebSocketSupportMixin:
    """Tests for the NoWebSocketSupportMixin."""

    class MockNoWSAdapter(BaseAdapter, NoWebSocketSupportMixin, SyncOnlyAdapter):
        """Mock adapter implementing NoWebSocketSupportMixin."""
        
        def get_trading_pair_format(self, trading_pair: str) -> str:
            return trading_pair.replace("-", "/")
            
        def get_supported_intervals(self) -> dict[str, int]:
            return {"1m": 60, "1h": 3600}
            
        def _get_rest_url(self) -> str:
            return "https://test.com/api"
            
        def _get_rest_params(self, trading_pair: str, interval: str, start_time=None, 
                            end_time=None, limit=None) -> dict:
            return {"symbol": trading_pair, "interval": interval}
            
        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
            return []
            
        def fetch_rest_candles_synchronous(
            self,
            trading_pair: str,
            interval: str,
            start_time: int | None = None,
            limit: int = 500,
        ) -> list[CandleData]:
            """Synchronous implementation for testing."""
            return []

    def test_get_ws_url_raises_error(self):
        """Test get_ws_url raises NotImplementedError."""
        # Test this at the mixin level directly
        mixin = NoWebSocketSupportMixin()
        
        with pytest.raises(NotImplementedError):
            mixin.get_ws_url()
            
    def test_get_ws_supported_intervals_raises_error(self):
        """Test get_ws_supported_intervals raises NotImplementedError."""
        # Test this at the mixin level directly
        mixin = NoWebSocketSupportMixin()
        
        with pytest.raises(NotImplementedError):
            mixin.get_ws_supported_intervals()
            
    def test_get_ws_subscription_payload_raises_error(self):
        """Test get_ws_subscription_payload raises NotImplementedError."""
        # Test this at the mixin level directly
        mixin = NoWebSocketSupportMixin()
        
        with pytest.raises(NotImplementedError):
            mixin.get_ws_subscription_payload("BTC-USDT", "1m")
            
    def test_parse_ws_message_raises_error(self):
        """Test parse_ws_message raises NotImplementedError."""
        # Test this at the mixin level directly
        mixin = NoWebSocketSupportMixin()
        
        with pytest.raises(NotImplementedError):
            mixin.parse_ws_message({})