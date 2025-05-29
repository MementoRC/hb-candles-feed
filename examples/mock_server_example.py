"""
Example of using the refactored MockedExchangeServer with ExchangeURLPatcher.

This example demonstrates how to set up and use the mock server with the plugin architecture,
showing the preferred approach after the refactoring.
"""

import asyncio
import logging
from contextlib import AsyncExitStack

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.server import MockedExchangeServer
from candles_feed.mocking_resources.core.url_patcher import ExchangeURLPatcher
from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import (
    BinanceSpotPlugin,
)


async def get_candles(adapter, trading_pair, interval):
    """Get candles from the adapter."""
    print(f"Getting candles for {trading_pair} {interval}")
    candles = await adapter.get_candles(trading_pair=trading_pair, interval=interval, limit=10)
    print(f"Got {len(candles)} candles")
    for i, candle in enumerate(candles[:3]):  # Just show first 3
        print(f"Candle {i}: {candle}")
    return candles


async def main():
    """Run the example."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create an AsyncExitStack for clean handling of async resources
    async with AsyncExitStack() as stack:
        print("Setting up mock server...")

        # Create the plugin
        plugin = BinanceSpotPlugin()

        # Create the mock server with the plugin
        server = MockedExchangeServer(plugin, "127.0.0.1", 8080)

        # Add some trading pairs
        server.add_trading_pair("BTC-USDT", "1m", 50000.0)
        server.add_trading_pair("ETH-USDT", "1m", 3000.0)

        # Start the server
        url = await server.start()
        print(f"Mock server started at {url}")

        # Make sure server is stopped on exit
        stack.push_async_callback(server.stop)

        # Create URL patcher to redirect adapter requests to our mock server
        patcher = ExchangeURLPatcher(ExchangeType.BINANCE_SPOT, "127.0.0.1", 8080)
        patcher.patch_urls(plugin)

        # Make sure URLs are restored on exit
        stack.push_callback(patcher.restore_urls)

        # Set simulated network conditions (optional)
        server.set_network_conditions(
            latency_ms=50,        # 50ms latency
            packet_loss_rate=0.0,  # No packet loss
            error_rate=0.0         # No errors
        )

        # Create and use the adapter
        adapter = BinanceSpotAdapter()

        # Get candles using the adapter (will be served by our mock server)
        await get_candles(adapter, "BTC-USDT", "1m")

        # Example of using WebSocket (would require WebSocket client implementation)
        print("Checking adapter connection status...")
        status = adapter.ready_for_rest_calls
        print(f"Adapter connection status: {status}")

        print("Example completed successfully")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
