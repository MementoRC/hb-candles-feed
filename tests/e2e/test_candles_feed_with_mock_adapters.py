"""
End-to-end tests for the Candles Feed with mock adapters.

These tests verify the complete workflow from adapter to candles feed.
"""

import asyncio

import pytest

from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.network_client import NetworkClient

# Import mock adapters to trigger their registration
import candles_feed.mocking_resources.adapter.async_mocked_adapter  # noqa: F401
import candles_feed.mocking_resources.adapter.hybrid_mocked_adapter  # noqa: F401
import candles_feed.mocking_resources.adapter.mocked_adapter  # noqa: F401
import candles_feed.mocking_resources.adapter.sync_mocked_adapter  # noqa: F401


@pytest.mark.asyncio
class TestCandlesFeedWithMockAdapters:
    """End-to-end tests for the Candles Feed with mock adapters."""

    @pytest.fixture
    async def network_client(self):
        """Fixture for network client instance."""
        client = NetworkClient()
        yield client
        # Make sure to close the client after the test
        await client.close()

    @pytest.mark.asyncio
    async def test_candles_feed_with_sync_adapter(self, network_client):
        """Test CandlesFeed with SyncMockedAdapter."""
        # Setup - SyncMockedAdapter should already be registered with ExchangeRegistry

        # Create the candles feed
        feed = CandlesFeed(
            trading_pair="BTC-USDT", exchange="sync_mocked_adapter", interval="1m", max_records=100
        )

        # Test the feed gets initialized with REST polling strategy
        await feed.start(strategy="polling")

        # Wait for initial data to populate
        await asyncio.sleep(0.1)

        # Verify we have candles data
        assert len(feed._candles) > 0

        # Check we can get candles data
        candles = feed.get_candles()
        assert len(candles) > 0

        # Stop the feed
        await feed.stop()

    @pytest.mark.asyncio
    async def test_candles_feed_with_async_adapter(self, network_client):
        """Test CandlesFeed with AsyncMockedAdapter."""
        # Setup - AsyncMockedAdapter should already be registered with ExchangeRegistry

        # Create the candles feed
        feed = CandlesFeed(
            trading_pair="BTC-USDT", exchange="async_mocked_adapter", interval="1m", max_records=100
        )

        # Test the feed gets initialized with REST polling strategy
        await feed.start(strategy="polling")

        # Wait for initial data to populate
        await asyncio.sleep(0.1)

        # Verify we have candles data
        assert len(feed._candles) > 0

        # Check we can get candles data
        candles = feed.get_candles()
        assert len(candles) > 0

        # Stop the feed
        await feed.stop()

    @pytest.mark.asyncio
    async def test_candles_feed_with_hybrid_adapter(self, network_client):
        """Test CandlesFeed with HybridMockedAdapter."""
        # Setup - HybridMockedAdapter should already be registered with ExchangeRegistry

        # Create the candles feed
        feed = CandlesFeed(
            trading_pair="BTC-USDT",
            exchange="hybrid_mocked_adapter",
            interval="1m",
            max_records=100,
        )

        # Test the feed gets initialized with REST polling strategy
        await feed.start(strategy="polling")

        # Wait for initial data to populate
        await asyncio.sleep(0.1)

        # Verify we have candles data
        assert len(feed._candles) > 0

        # Check we can get candles data
        candles = feed.get_candles()
        assert len(candles) > 0
        assert candles[0].open > 0  # Should have valid data

        # Verify it's using the async implementation (values start at 200)
        # Since the feed uses RESTPollingStrategy, it will call fetch_rest_candles
        assert candles[0].open >= 200

        # Stop the feed
        await feed.stop()

    @pytest.mark.asyncio
    async def test_multiple_candles_feeds_concurrently(self, network_client):
        """Test running multiple CandlesFeeds concurrently with different adapters."""
        # Setup - all adapters should already be registered with ExchangeRegistry

        # Create feeds
        sync_feed = CandlesFeed(
            trading_pair="BTC-USDT", exchange="sync_mocked_adapter", interval="1m", max_records=100
        )

        async_feed = CandlesFeed(
            trading_pair="ETH-USDT", exchange="async_mocked_adapter", interval="5m", max_records=100
        )

        hybrid_feed = CandlesFeed(
            trading_pair="LTC-USDT",
            exchange="hybrid_mocked_adapter",
            interval="15m",
            max_records=100,
        )

        # Start all feeds with REST polling strategy
        await asyncio.gather(
            sync_feed.start(strategy="polling"),
            async_feed.start(strategy="polling"),
            hybrid_feed.start(strategy="polling"),
        )

        # Wait for all feeds to initialize
        await asyncio.sleep(0.2)

        # Verify all feeds have data
        sync_candles = sync_feed.get_candles()
        async_candles = async_feed.get_candles()
        hybrid_candles = hybrid_feed.get_candles()

        assert len(sync_candles) > 0
        assert len(async_candles) > 0
        assert len(hybrid_candles) > 0

        # Each adapter should produce valid data
        assert sync_candles[0].open > 0  # From sync adapter
        assert async_candles[0].open > 0  # From async adapter
        assert hybrid_candles[0].open > 0  # From hybrid adapter

        # Stop all feeds
        await asyncio.gather(sync_feed.stop(), async_feed.stop(), hybrid_feed.stop())
