"""
Integration tests for the mock adapters with collection strategies and mock server.

This module tests:
1. Mock adapters (Sync, Async, Hybrid) with collection strategies
2. Direct interaction with the mock server via REST and WebSocket
3. CandlesFeed integration with mock adapters
"""

import asyncio
from collections import deque
from unittest.mock import AsyncMock, Mock

import pytest

from candles_feed.core.collection_strategies import (
    CollectionStrategyFactory,
    RESTPollingStrategy,
    WebSocketStrategy,
)
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.network_client import NetworkClient
from candles_feed.mocking_resources.adapter import (
    AsyncMockedAdapter,
    HybridMockedAdapter,
    SyncMockedAdapter,
)


@pytest.mark.asyncio
class TestMockAdaptersWithStrategies:
    """Test how mock adapters interact with collection strategies."""

    @pytest.fixture
    def data_processor(self):
        """Fixture for data processor instance."""
        return DataProcessor()

    @pytest.fixture
    def candles_store(self):
        """Fixture for candles store deque."""
        return deque(maxlen=100)

    @pytest.fixture
    async def network_client(self):
        """Fixture for network client instance."""
        client = NetworkClient()
        yield client
        # Make sure to close the client after the test
        await client.close()

    @pytest.mark.asyncio
    async def test_sync_adapter_with_rest_strategy(
        self, data_processor, candles_store, network_client
    ):
        """Test SyncMockedAdapter with RESTPollingStrategy."""
        # Setup
        adapter = SyncMockedAdapter()
        strategy = RESTPollingStrategy(
            network_client=network_client,
            adapter=adapter,
            trading_pair="BTC-USDT",
            interval="1m",
            data_processor=data_processor,
            candles_store=candles_store,
        )

        # Test poll_once
        candles = await strategy.poll_once(limit=10)

        # Verify we got the expected candles
        assert len(candles) == 10
        assert candles[0].open == 100.0
        assert candles[1].open == 101.0
        assert candles[-1].open == 109.0

        # Verify candles are timestamp-ordered
        timestamps = [c.timestamp for c in candles]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_async_adapter_with_rest_strategy(
        self, data_processor, candles_store, network_client
    ):
        """Test AsyncMockedAdapter with RESTPollingStrategy."""
        # Setup
        adapter = AsyncMockedAdapter(network_client=network_client)
        strategy = RESTPollingStrategy(
            network_client=network_client,
            adapter=adapter,
            trading_pair="BTC-USDT",
            interval="1m",
            data_processor=data_processor,
            candles_store=candles_store,
        )

        # Test poll_once
        candles = await strategy.poll_once(limit=10)

        # Verify we got the expected candles
        assert len(candles) == 10
        assert candles[0].open == 100.0
        assert candles[1].open == 101.0
        assert candles[-1].open == 109.0

    @pytest.mark.asyncio
    async def test_hybrid_adapter_with_rest_strategy(
        self, data_processor, candles_store, network_client
    ):
        """Test HybridMockedAdapter with RESTPollingStrategy."""
        # Setup
        adapter = HybridMockedAdapter(network_client=network_client)
        strategy = RESTPollingStrategy(
            network_client=network_client,
            adapter=adapter,
            trading_pair="BTC-USDT",
            interval="1m",
            data_processor=data_processor,
            candles_store=candles_store,
        )

        # Test poll_once using the async method
        candles = await strategy.poll_once(limit=10)

        # Verify we got the expected candles from the async method
        # (the async method in hybrid adapter produces different values)
        assert len(candles) == 10
        assert candles[0].open == 200.0
        assert candles[1].open == 202.0
        assert candles[-1].open == 218.0

    @pytest.mark.asyncio
    async def test_factory_selects_websocket_strategy(
        self, data_processor, candles_store, network_client
    ):
        """Test CollectionStrategyFactory selects WebSocketStrategy for adapters with WS support."""
        # Setup
        adapter = HybridMockedAdapter()

        # Mock network client methods that would be used by WebSocketStrategy
        mock_ws_assistant = AsyncMock()
        network_client.establish_ws_connection = AsyncMock(return_value=mock_ws_assistant)
        network_client.send_ws_message = AsyncMock()

        # Use the factory to create the strategy
        strategy = CollectionStrategyFactory.create_strategy(
            adapter=adapter,
            trading_pair="BTC-USDT",
            interval="1m",
            network_client=network_client,
            data_processor=data_processor,
            candles_store=candles_store,
        )

        # Verify it's a WebSocketStrategy
        assert isinstance(strategy, WebSocketStrategy)

    @pytest.mark.asyncio
    async def test_factory_gracefully_handles_websocket_not_supported(
        self, data_processor, candles_store, network_client
    ):
        """Test factory handles adapters that raise NotImplementedError for WebSocket."""
        # Setup
        adapter = HybridMockedAdapter()

        # Patch get_ws_supported_intervals to raise NotImplementedError
        adapter.get_ws_supported_intervals = Mock(side_effect=NotImplementedError)

        # Use the factory to create the strategy
        strategy = CollectionStrategyFactory.create_strategy(
            adapter=adapter,
            trading_pair="BTC-USDT",
            interval="1m",
            network_client=network_client,
            data_processor=data_processor,
            candles_store=candles_store,
        )

        # Verify it's a RESTPollingStrategy
        assert isinstance(strategy, RESTPollingStrategy)

    @pytest.mark.asyncio
    async def test_adapter_with_collection_strategy_lifecycle(
        self, data_processor, candles_store, network_client
    ):
        """Test full lifecycle of adapter with collection strategy."""
        # Setup
        adapter = AsyncMockedAdapter(network_client=network_client)
        strategy = RESTPollingStrategy(
            network_client=network_client,
            adapter=adapter,
            trading_pair="BTC-USDT",
            interval="1m",
            data_processor=data_processor,
            candles_store=candles_store,
        )

        # Start the strategy
        await strategy.start()

        # Wait for the initial poll to complete
        await asyncio.sleep(0.1)

        # Verify the candles store was populated
        assert len(candles_store) > 0

        # Stop the strategy
        await strategy.stop()

        # Verify the polling task was cancelled
        assert strategy._polling_task is None
