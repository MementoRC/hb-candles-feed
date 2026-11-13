"""
End-to-end test for the Candles Feed framework.

This module demonstrates how to use the exchange simulation framework
to test the Candles Feed in a realistic but controlled environment.
"""

import asyncio
import logging

import pandas as pd
import pytest

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.factory import get_plugin
from candles_feed.mocking_resources.core.server import MockedExchangeServer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEndToEnd:
    """End-to-end test suite for the Candles Feed."""

    @pytest.fixture
    async def local_binance_server(self, unused_tcp_port, redirect_rest):
        """Run a mock Binance server and point the Binance Spot adapter's REST URL at it."""
        plugin = get_plugin(ExchangeType.BINANCE_SPOT)
        host = "127.0.0.1"
        port = unused_tcp_port

        server = MockedExchangeServer(plugin, host, port)

        # These need to match what the tests will request
        server.add_trading_pair("BTC-USDT", "1m", initial_price=50000.0)
        server.add_trading_pair("ETH-USDT", "1m", initial_price=3000.0)

        await server.start()

        server.mock_rest_url_base = f"http://{host}:{port}"
        # BinanceBasePlugin serves its WebSocket at /ws
        server.mock_ws_url = f"ws://{host}:{port}/ws"

        redirect_rest(BinanceSpotAdapter, server.mock_rest_url_base)

        yield server

        await server.stop()

    async def test_rest_candles_retrieval(self, local_binance_server):
        """Test retrieving candles via REST API from the local mock server."""
        # Create a CandlesFeed instance
        feed = CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100
        )

        try:
            # Fetch historical candles
            logger.info("Fetching candles via REST API...")
            candles = await feed.fetch_candles()

            # Verify candles were received
            assert len(candles) > 0, "No candles received"
            logger.info(f"Successfully received {len(candles)} candles via local mock REST")

            # fetch_candles returns data only; the live store stays untouched
            assert feed.get_candles() == []

            # Convert to DataFrame for easier inspection
            df = pd.DataFrame(
                [
                    {"open": c.open, "high": c.high, "low": c.low, "volume": c.volume}
                    for c in candles
                ]
            )
            logger.info(f"First candle: {df.iloc[0].to_dict()}")
            logger.info(f"Last candle: {df.iloc[-1].to_dict()}")

            # Verify candle data looks reasonable
            assert all(df["open"] > 0), "Open prices should be positive"
            assert all(df["high"] >= df["open"]), "High should be >= open"
            assert all(df["low"] <= df["open"]), "Low should be <= open"
            assert all(df["volume"] > 0), "Volume should be positive"

        finally:
            # Clean up resources
            await feed.stop()

    async def test_multiple_trading_pairs(self, local_binance_server):
        """Test working with multiple trading pairs simultaneously."""
        # Create feeds for different trading pairs
        btc_feed = CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100
        )

        eth_feed = CandlesFeed(
            exchange="binance_spot", trading_pair="ETH-USDT", interval="1m", max_records=100
        )

        try:
            # Fetch historical data for both feeds
            btc_candles, eth_candles = await asyncio.gather(
                btc_feed.fetch_candles(), eth_feed.fetch_candles()
            )

            # Verify candles were received for each feed
            assert len(btc_candles) > 0, "No BTC candles received"
            assert len(eth_candles) > 0, "No ETH candles received"

            # Compare prices to ensure they're different (as expected for different assets)
            btc_price = btc_candles[-1].close
            eth_price = eth_candles[-1].close

            logger.info(f"Latest prices via local mock - BTC: {btc_price}, ETH: {eth_price}")

            # Prices should be in different ranges based on our mock server configuration
            assert 35000 < btc_price < 65000, "BTC price should be somewhere around 50000"
            assert 1500 < eth_price < 4500, "ETH price should be somewhere around 3000"

        finally:
            # Clean up resources
            await asyncio.gather(btc_feed.stop(), eth_feed.stop())


if __name__ == "__main__":
    # This allows running the test directly
    pytest.main(["-xvs", __file__])
