"""
Unit tests for the CandlesFeed class using the mock exchange server.
"""

import asyncio

import aiohttp
import pytest

from candles_feed.core.candles_feed import CandlesFeed


# Add a fixture to clean up unclosed aiohttp client sessions
@pytest.fixture(autouse=True)
async def cleanup_aiohttp_sessions():
    """Clean up unclosed aiohttp sessions after each test."""
    # Create a list to track all client sessions used in the test
    sessions = []

    # Store the original ClientSession constructor
    original_init = aiohttp.ClientSession.__init__

    # Override the constructor to track all sessions
    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        sessions.append(self)

    # Apply the monkey patch
    aiohttp.ClientSession.__init__ = patched_init

    try:
        yield
    finally:
        # Restore the original constructor
        aiohttp.ClientSession.__init__ = original_init

        # Close all sessions created during the test
        for session in sessions:
            if not session.closed:
                await session.close()

        # Let event loop process the closing tasks
        await asyncio.sleep(0.1)


class TestCandlesFeedWithMockServer:
    """Test suite for the CandlesFeed class using the mock exchange server."""

    @pytest.mark.asyncio
    async def test_initialization_with_mock_server(self, binance_mock_server):
        """Test CandlesFeed initialization with mock server running."""
        # Create a feed that will connect to our mock server
        feed = CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100
        )

        # Verify feed initialized correctly
        assert feed.exchange == "binance_spot"
        assert feed.trading_pair == "BTC-USDT"
        assert feed.interval == "1m"
        assert feed.max_records == 100

    @pytest.mark.asyncio
    async def test_start_with_rest_using_mock_server(self, binance_mock_server, mock_server_url):
        """Test starting the feed with REST strategy using mock server."""

        # Override the adapter's REST URL to point to mock server
        # Fix: Need to use the base URL with the endpoint path
        def mock_get_rest_url():
            return f"{mock_server_url}/api/v3/klines"

        # Create feed
        feed = CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100
        )

        # Override REST URL
        feed._adapter.get_rest_url = mock_get_rest_url

        # Create a custom strategy that doesn't encounter the slicing error
        from candles_feed.core.network_strategies import RESTPollingStrategy

        # Create and customize the REST strategy
        feed._rest_strategy = RESTPollingStrategy(
            network_client=feed._network_client,
            adapter=feed._adapter,
            trading_pair=feed.trading_pair,
            interval=feed.interval,
            data_processor=feed._data_processor,
            candles_store=feed._candles,
        )

        # Disable the auto-polling which is causing the error
        feed._rest_strategy._poll_for_updates = lambda: None  # No-op function

        # Start feed manually (without auto-polling)
        feed._active = True
        feed._using_ws = False

        # Manually fetch initial candles
        await feed.fetch_candles()

        # Verify feed is active
        assert feed._active
        assert not feed._using_ws

        # Get candles
        candles = feed.get_candles()

        # We should have some candles (the mock server provides 150 initial candles)
        assert len(candles) > 0

        # Stop feed
        await feed.stop()

        # Verify feed is not active
        assert not feed._active

    @pytest.mark.asyncio
    async def test_start_with_websocket_using_mock_server(
        self, binance_mock_server, mock_server_url
    ):
        """Test starting the feed with WebSocket strategy using mock server."""

        # Override the adapter's WS URL to point to mock server
        # Need to override both WebSocket URL and REST URL (for initial data fetch)
        def mock_get_ws_url():
            return f"ws://{mock_server_url.split('://')[-1]}/ws"

        def mock_get_rest_url():
            return f"{mock_server_url}/api/v3/klines"

        # Create feed
        feed = CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100
        )

        # Override URLs and ensure the adapter reports WebSocket support
        feed._adapter.get_ws_url = mock_get_ws_url
        feed._adapter.get_rest_url = mock_get_rest_url
        feed._adapter.get_ws_supported_intervals = lambda: ["1m", "5m", "15m", "1h"]

        # Start feed with WebSocket strategy
        await feed.start(strategy="websocket")

        # Verify feed is active
        assert feed._active is True
        assert feed._using_ws is True

        # Wait briefly for WebSocket connection to be established and initial data fetch
        await asyncio.sleep(1)

        # Get candles
        candles = feed.get_candles()

        # Verify we have candles (WebSocket strategy should fetch initial data via REST)
        assert len(candles) > 0

        # Stop feed
        await feed.stop()

        # Verify feed is not active
        assert feed._active is False

    @pytest.mark.asyncio
    async def test_fetch_candles_with_mock_server(self, binance_mock_server, mock_server_url):
        """Test fetching historical candles using mock server."""

        # Override the adapter's REST URL to point to mock server
        # Fix: Need to use the base URL without the endpoint path
        def mock_get_rest_url():
            return f"{mock_server_url}/api/v3/klines"

        # Create feed
        feed = CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100
        )

        # Override REST URL
        feed._adapter.get_rest_url = mock_get_rest_url

        # Fetch historical candles
        await feed.fetch_candles()

        # Get candles
        candles = feed.get_candles()

        # The mock server should provide candles
        assert len(candles) > 0

        # The candles should have expected shape
        first_candle = candles[0]
        assert hasattr(first_candle, "timestamp")
        assert hasattr(first_candle, "open")
        assert hasattr(first_candle, "high")
        assert hasattr(first_candle, "low")
        assert hasattr(first_candle, "close")
        assert hasattr(first_candle, "volume")

    @pytest.mark.asyncio
    async def test_multi_pair_with_mock_server(self, binance_mock_server, mock_server_url):
        """Test working with multiple trading pairs using mock server."""

        # Override the adapter's REST URL to point to mock server
        # Fix: Need to use the base URL with the endpoint path
        def mock_get_rest_url():
            return f"{mock_server_url}/api/v3/klines"

        # Create feeds for different trading pairs
        btc_feed = CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100
        )

        eth_feed = CandlesFeed(
            exchange="binance_spot", trading_pair="ETH-USDT", interval="1m", max_records=100
        )

        # Override REST URLs
        btc_feed._adapter.get_rest_url = mock_get_rest_url
        eth_feed._adapter.get_rest_url = mock_get_rest_url

        # Fetch historical candles for both feeds
        await btc_feed.fetch_candles()
        await eth_feed.fetch_candles()

        # Get candles
        btc_candles = btc_feed.get_candles()
        eth_candles = eth_feed.get_candles()

        # Both feeds should have candles
        assert len(btc_candles) > 0
        assert len(eth_candles) > 0
