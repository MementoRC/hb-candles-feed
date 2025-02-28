"""
End-to-end tests for the Candles Feed framework.

These tests use a mock exchange server to simulate real API interactions.
"""

import asyncio
import logging
from datetime import datetime, timezone

import pytest

from candles_feed.core.candles_feed import CandlesFeed
from tests.mocks.mock_exchange_server import MockExchangeServer


class TestCandlesFeedE2E:
    """End-to-end test suite for the CandlesFeed class."""

    @pytest.fixture
    async def mock_server(self):
        """Set up and tear down a mock exchange server."""
        server = MockExchangeServer(host='127.0.0.1', port=8080)
        await server.start()

        # Add some trading pairs
        server.add_trading_pair("BTCUSDT", "1m", initial_price=50000.0)
        server.add_trading_pair("ETHUSDT", "1m", initial_price=3000.0)

        yield server

        await server.stop()

    @pytest.mark.asyncio
    async def test_rest_candles_retrieval(self, mock_server):
        """Test retrieving candles via REST API."""
        # Patch the REST URL to point to our mock server (primarily for Binance)
        import candles_feed.adapters.binance_spot.constants as binance_constants
        from candles_feed.adapters.binance_spot.constants import REST_URL as BINANCE_REST_URL
        original_rest_url = BINANCE_REST_URL

        try:
            # Override the REST URL to point to our mock server
            binance_constants.REST_URL = "http://127.0.0.1:8080"

            # Create a CandlesFeed for Binance
            feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100
            )

            # Fetch historical candles
            await feed.fetch_candles()

            # Verify candles were received
            candles = feed.get_candles()
            assert len(candles) > 0

            # Check the data makes sense
            assert all(45000 < candle.open < 55000 for candle in candles)  # Price around 50000
            assert all(candle.high >= candle.open for candle in candles)
            assert all(candle.low <= candle.open for candle in candles)
            assert all(candle.volume > 0 for candle in candles)

        finally:
            # Restore the original URL
            binance_constants.REST_URL = original_rest_url

    @pytest.mark.asyncio
    async def test_websocket_candles_streaming(self, mock_server):
        """Test streaming candles via WebSocket."""
        # Patch the WebSocket URL to point to our mock server
        import candles_feed.adapters.binance_spot.constants as binance_constants
        from candles_feed.adapters.binance_spot.constants import WSS_URL as BINANCE_WSS_URL
        original_ws_url = BINANCE_WSS_URL

        try:
            # Override the WebSocket URL to point to our mock server
            binance_constants.WSS_URL = "ws://127.0.0.1:8080/ws"

            # Create a CandlesFeed for Binance
            feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100
            )

            # Start the feed with WebSocket
            await feed.start(strategy="websocket")

            # Wait for some candles to arrive
            for _ in range(10):
                if len(feed.get_candles()) > 0:
                    break
                await asyncio.sleep(0.2)

            # Verify candles were received
            candles = feed.get_candles()
            assert len(candles) > 0

            # Wait a bit longer to receive more candles
            initial_count = len(candles)
            await asyncio.sleep(1.5)  # Wait for more updates

            # Verify more candles arrived
            updated_candles = feed.get_candles()
            assert len(updated_candles) >= initial_count

            # Stop the feed
            await feed.stop()

        finally:
            # Restore the original URL
            binance_constants.WSS_URL = original_ws_url

    @pytest.mark.asyncio
    async def test_multiple_feeds(self, mock_server):
        """Test running multiple feeds simultaneously."""
        # Patch the URLs to point to our mock server
        import candles_feed.adapters.binance_spot.constants as binance_constants
        from candles_feed.adapters.binance_spot.constants import REST_URL as BINANCE_REST_URL
        from candles_feed.adapters.binance_spot.constants import WSS_URL as BINANCE_WSS_URL
        original_rest_url = BINANCE_REST_URL
        original_ws_url = BINANCE_WSS_URL

        try:
            # Override the URLs to point to our mock server
            binance_constants.REST_URL = "http://127.0.0.1:8080"
            binance_constants.WSS_URL = "ws://127.0.0.1:8080/ws"

            # Create two feeds for different trading pairs
            btc_feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100
            )

            eth_feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair="ETH-USDT",
                interval="1m",
                max_records=100
            )

            # Start both feeds
            await btc_feed.start(strategy="websocket")
            await eth_feed.start(strategy="websocket")

            # Wait for some candles to arrive
            for _ in range(10):
                if len(btc_feed.get_candles()) > 0 and len(eth_feed.get_candles()) > 0:
                    break
                await asyncio.sleep(0.2)

            # Verify both feeds received candles
            btc_candles = btc_feed.get_candles()
            eth_candles = eth_feed.get_candles()

            assert len(btc_candles) > 0
            assert len(eth_candles) > 0

            # Verify the price ranges are different (BTC around 50000, ETH around 3000)
            assert all(45000 < candle.open < 55000 for candle in btc_candles)
            assert all(2700 < candle.open < 3300 for candle in eth_candles)

            # Stop both feeds
            await btc_feed.stop()
            await eth_feed.stop()

        finally:
            # Restore the original URLs
            binance_constants.REST_URL = original_rest_url
            binance_constants.WSS_URL = original_ws_url
