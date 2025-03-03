"""
Example demonstrating how to use the MockedCandlesFeedServer for end-to-end testing.

This example shows how to:
1. Set up a MockedCandlesFeedServer for a specific exchange
2. Configure it with custom trading pairs and initial prices
3. Test CandlesFeed with REST and WebSocket strategies
4. Simulate network conditions like latency and errors
"""

import asyncio
import logging
from typing import List

import pandas as pd
import pytest

from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.testing_resources.mocked_candle_feed_server import MockedCandlesFeedServer
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Example of using MockedCandlesFeedServer with CandlesFeed."""
    # Create and start a test exchange server for Binance Spot
    server = MockedCandlesFeedServer(
        exchange_type=ExchangeType.BINANCE_SPOT, host="127.0.0.1", port=8789
    )

    # Configure custom trading pairs
    custom_pairs = [
        ("BTCUSDT", "1m", 50000.0),  # BTC with initial price of $50,000
        ("ETHUSDT", "1m", 3000.0),  # ETH with initial price of $3,000
        ("SOLUSDT", "1m", 100.0),  # SOL with initial price of $100
        ("BTCUSDT", "5m", 50000.0),  # Also add BTC with 5m interval
        ("BTCUSDT", "1h", 50000.0),  # And with 1h interval
    ]

    try:
        # Start the server with our custom pairs
        await server.start(trading_pairs=custom_pairs)
        logger.info(f"Mock exchange server started at {server.url}")

        # Create CandlesFeed instances for different trading pairs
        feeds = []

        # BTC feed with different intervals
        for interval in ["1m", "5m", "1h"]:
            feed = CandlesFeed(
                exchange="binance_spot", trading_pair="BTC-USDT", interval=interval, max_records=100
            )
            feeds.append((f"BTC-USDT {interval}", feed))

        # Add ETH and SOL feeds
        eth_feed = CandlesFeed(
            exchange="binance_spot", trading_pair="ETH-USDT", interval="1m", max_records=100
        )
        feeds.append(("ETH-USDT 1m", eth_feed))

        sol_feed = CandlesFeed(
            exchange="binance_spot", trading_pair="SOL-USDT", interval="1m", max_records=100
        )
        feeds.append(("SOL-USDT 1m", sol_feed))

        # Step 1: Test REST API
        logger.info("Testing REST API...")
        for name, feed in feeds:
            # Fetch historical candles
            candles = await feed.fetch_candles()

            # Print candle info
            logger.info(f"{name}: Received {len(candles)} candles")
            if candles:
                df = feed.get_candles_df()
                logger.info(f"{name}: Price range: {df['low'].min()} - {df['high'].max()}")

        # Step 2: Test WebSocket API
        logger.info("\nTesting WebSocket API...")

        # Take the BTC 1m feed for WebSocket testing
        btc_feed = next(feed for name, feed in feeds if name == "BTC-USDT 1m")

        # Start the feed with WebSocket
        await btc_feed.start(strategy="websocket")

        # Wait for some updates
        logger.info("Waiting for WebSocket updates...")
        for i in range(10):
            candles = btc_feed.get_candles()
            if candles:
                logger.info(f"[{i}] Current BTC price: {candles[-1].close}")
            await asyncio.sleep(1)

        # Step 3: Test network condition simulation
        logger.info("\nTesting network conditions...")

        # Set moderate error simulation
        server.set_network_conditions(
            latency_ms=200,  # 200ms latency
            packet_loss_rate=0.1,  # 10% packet loss
            error_rate=0.1,  # 10% error responses
        )

        logger.info("Set difficult network conditions (latency, packet loss, errors)")

        # Try to fetch data under poor conditions
        eth_price_before = eth_feed.get_candles()[-1].close if eth_feed.get_candles() else None

        for retry in range(5):
            try:
                logger.info(
                    f"Attempt {retry + 1} to fetch ETH candles under difficult conditions..."
                )
                await eth_feed.fetch_candles()
                logger.info("Successfully fetched despite errors!")
                break
            except Exception as e:
                logger.info(f"Error as expected: {e}")
                await asyncio.sleep(0.5)

        # Reset network conditions
        server.set_network_conditions(latency_ms=0, packet_loss_rate=0.0, error_rate=0.0)
        logger.info("Reset network conditions to normal")

        # One more fetch should work reliably now
        await eth_feed.fetch_candles()
        eth_price_after = eth_feed.get_candles()[-1].close if eth_feed.get_candles() else None

        if eth_price_before and eth_price_after:
            price_change = abs(eth_price_after - eth_price_before)
            logger.info(f"ETH price changed by {price_change} after network condition test")

    finally:
        # Clean up
        logger.info("\nCleaning up...")

        # Stop all feeds
        for name, feed in feeds:
            try:
                await feed.stop()
                logger.info(f"Stopped feed: {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")

        # Stop the server
        await server.stop()
        logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
