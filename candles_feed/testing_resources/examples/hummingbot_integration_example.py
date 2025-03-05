"""
Example demonstrating how to use CandlesFeed with Hummingbot components.

This example shows how to integrate CandlesFeed with Hummingbot's network components.
"""

import asyncio
import logging
from typing import Dict, List

# Import from candles_feed
from candles_feed import create_candles_feed_with_hummingbot

# Hummingbot imports would be here in an actual Hummingbot instance
# For demonstration purposes, we'll use our mocks
from candles_feed.testing_resources.mocks.hummingbot.mock_components import (
    create_mock_hummingbot_components,
)


async def main():
    """Run the example.
    
    This demonstrates how to use the CandlesFeed with Hummingbot's networking components.
    """
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("hummingbot_integration_example")

    # In a real Hummingbot instance, you would get these from the Hummingbot environment
    # For demonstration, we'll create mock components
    logger.info("Creating mock Hummingbot components")
    mock_components = create_mock_hummingbot_components()
    throttler = mock_components["throttler"]
    web_assistants_factory = mock_components["web_assistants_factory"]

    # Create a CandlesFeed instance with Hummingbot components
    logger.info("Creating CandlesFeed with Hummingbot components")
    candles_feed = create_candles_feed_with_hummingbot(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        throttler=throttler,
        web_assistants_factory=web_assistants_factory,
        logger=logger,
    )

    try:
        # Start the feed
        logger.info("Starting the feed")
        await candles_feed.start()

        # Wait for some candles to be collected
        logger.info("Waiting for candles to be collected...")
        for _ in range(10):
            await asyncio.sleep(1)
            candles = candles_feed.get_candles()
            if candles:
                logger.info(f"Collected {len(candles)} candles")
                break

        # Get the candles as a DataFrame
        df = candles_feed.get_candles_df()
        logger.info(f"Candles DataFrame shape: {df.shape}")
        
        if not df.empty:
            logger.info(f"Latest close price: {df.iloc[-1]['close']}")

    finally:
        # Always stop the feed to clean up resources
        logger.info("Stopping the feed")
        await candles_feed.stop()


"""
In an actual Hummingbot strategy, you would use the CandlesFeed like this:

from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.connections.connections_factory import ConnectionsFactory
from hummingbot.data_feed import create_candles_feed_with_hummingbot

class MyStrategy:
    def __init__(self, ...):
        # Set up Hummingbot's networking components
        self._throttler = AsyncThrottler(rate_limits=[...])
        self._connections_factory = ConnectionsFactory()
        self._web_assistants_factory = WebAssistantsFactory(
            throttler=self._throttler,
            connections_factory=self._connections_factory
        )
        
        # Create a CandlesFeed instance that uses Hummingbot's components
        self._candles_feed = create_candles_feed_with_hummingbot(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            throttler=self._throttler,
            web_assistants_factory=self._web_assistants_factory
        )
    
    async def start(self, ...):
        # Start the feed
        await self._candles_feed.start()
        
    async def stop(self, ...):
        # Stop the feed
        await self._candles_feed.stop()
        
    def process_candles(self):
        # Get candles as DataFrame
        df = self._candles_feed.get_candles_df()
        # Use the DataFrame for analysis, etc.
"""


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Example terminated by user")
    finally:
        loop.close()