# Mock Server Example

This example demonstrates how to use the mock server functionality for testing the Candles Feed framework without connecting to real exchanges. This is particularly useful for development, testing, and CI/CD pipelines.

## Basic Server Setup

```python
import asyncio
import logging
from candles_feed.testing_resources.mocked_candle_feed_server import MockedCandlesFeedServer
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Example of setting up and using a mock exchange server."""
    # Create a mock server for Binance Spot
    server = MockedCandlesFeedServer(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host="127.0.0.1",
        port=8080
    )
    
    # Configure custom trading pairs
    custom_pairs = [
        ("BTCUSDT", "1m", 50000.0),  # BTC with initial price of $50,000
        ("ETHUSDT", "1m", 3000.0),   # ETH with initial price of $3,000
        ("SOLUSDT", "1m", 100.0),    # SOL with initial price of $100
        ("BTCUSDT", "5m", 50000.0),  # BTC with 5m interval
        ("BTCUSDT", "1h", 50000.0),  # BTC with 1h interval
    ]
    
    try:
        # Start the server with our custom pairs
        await server.start(trading_pairs=custom_pairs)
        logger.info(f"Mock exchange server started at {server.url}")
        
        # Now you can use the server for testing
        # ...
        
        # Let it run for a while to see the logs
        await asyncio.sleep(5)
        
    finally:
        # Always stop the server when done
        await server.stop()
        logger.info("Server stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

## Using the Mock Server with CandlesFeed

This example shows how to connect CandlesFeed to the mock server:

```python
import asyncio
import logging
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.testing_resources.mocked_candle_feed_server import MockedCandlesFeedServer
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Example of using CandlesFeed with a mock server."""
    # Create and start a mock server
    server = MockedCandlesFeedServer(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host="127.0.0.1",
        port=8080
    )
    
    # Start with standard trading pairs
    await server.start()
    logger.info(f"Mock server started at {server.url}")
    
    # Create a CandlesFeed instance
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        max_records=100
    )
    
    # Override the adapter's URL methods to point to our mock server
    feed._adapter.get_rest_url = lambda: f"{server.url}/api/v3/klines"
    feed._adapter.get_ws_url = lambda: f"ws://{server.host}:{server.port}/ws"
    
    try:
        # Try both REST and WebSocket strategies
        
        # 1. First, use REST polling
        logger.info("Testing REST polling strategy...")
        await feed.start(strategy="polling")
        
        # Wait a bit for data to accumulate
        await asyncio.sleep(2)
        
        # Check the results
        candles = feed.get_candles()
        logger.info(f"Received {len(candles)} candles via REST")
        if candles:
            logger.info(f"Latest BTC price: {candles[-1].close}")
        
        # Stop the feed
        await feed.stop()
        
        # 2. Now, use WebSocket
        logger.info("\nTesting WebSocket strategy...")
        await feed.start(strategy="websocket")
        
        # Wait for some updates
        for i in range(5):
            await asyncio.sleep(1)
            candles = feed.get_candles()
            if candles:
                logger.info(f"[WS Update {i+1}] BTC price: {candles[-1].close}")
        
    finally:
        # Clean up
        await feed.stop()
        await server.stop()
        logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing Network Conditions

This example demonstrates how to simulate different network conditions to test error handling:

```python
import asyncio
import logging
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.testing_resources.mocked_candle_feed_server import MockedCandlesFeedServer
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Example of testing with difficult network conditions."""
    # Create and start a mock server
    server = MockedCandlesFeedServer(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host="127.0.0.1",
        port=8080
    )
    
    await server.start()
    logger.info(f"Mock server started at {server.url}")
    
    # Create a CandlesFeed instance
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        max_records=100
    )
    
    # Override the adapter's URL methods
    feed._adapter.get_rest_url = lambda: f"{server.url}/api/v3/klines"
    feed._adapter.get_ws_url = lambda: f"ws://{server.host}:{server.port}/ws"
    
    try:
        # First, get data with normal conditions
        logger.info("Fetching data with normal network conditions...")
        await feed.fetch_candles()
        normal_candles = len(feed.get_candles())
        logger.info(f"Received {normal_candles} candles")
        
        # Now simulate difficult network conditions
        logger.info("\nSetting difficult network conditions...")
        server.set_network_conditions(
            latency_ms=500,       # 500ms latency
            packet_loss_rate=0.3, # 30% packet loss
            error_rate=0.3        # 30% error responses
        )
        
        # Try to fetch data under these conditions
        logger.info("Attempting to fetch data with difficult conditions...")
        success_count = 0
        error_count = 0
        
        for i in range(5):
            try:
                logger.info(f"Attempt {i+1}...")
                await feed.fetch_candles()
                success_count += 1
                logger.info("Success!")
            except Exception as e:
                error_count += 1
                logger.warning(f"Failed: {str(e)}")
            
            await asyncio.sleep(1)
        
        logger.info(f"\nResults: {success_count} successes, {error_count} failures")
        
        # Reset to normal conditions
        logger.info("\nResetting to normal network conditions...")
        server.set_network_conditions(
            latency_ms=0,
            packet_loss_rate=0.0,
            error_rate=0.0
        )
        
        # Try one more fetch
        logger.info("Fetching data with normal conditions again...")
        await feed.fetch_candles()
        new_count = len(feed.get_candles())
        logger.info(f"Received {new_count} candles")
        
    finally:
        # Clean up
        await feed.stop()
        await server.stop()
        logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing Rate Limiting

This example shows how to test rate limiting behavior:

```python
import asyncio
import logging
import time
from candles_feed.testing_resources.mocked_candle_feed_server import MockedCandlesFeedServer
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType
import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Example of testing rate limiting."""
    # Create and start a mock server
    server = MockedCandlesFeedServer(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host="127.0.0.1",
        port=8080
    )
    
    await server.start()
    logger.info(f"Mock server started at {server.url}")
    
    # Set custom rate limits
    server.set_rate_limits(
        rest_limit=5,        # Only 5 requests
        rest_period_ms=5000, # Per 5 seconds
        ws_limit=2,          # 2 messages
        ws_burst=3           # Burst of 3 allowed
    )
    
    try:
        # Create an HTTP session for testing
        async with aiohttp.ClientSession() as session:
            # Make requests in a loop to hit the rate limit
            logger.info("Making rapid requests to test rate limiting...")
            
            success_count = 0
            rate_limited_count = 0
            
            # Try to make 10 requests quickly
            for i in range(10):
                try:
                    start_time = time.time()
                    
                    # Make a request to the klines endpoint
                    url = f"{server.url}/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=10"
                    async with session.get(url) as response:
                        elapsed = time.time() - start_time
                        
                        if response.status == 200:
                            success_count += 1
                            logger.info(f"Request {i+1}: Success ({elapsed:.2f}s)")
                        elif response.status == 429:  # Too Many Requests
                            rate_limited_count += 1
                            logger.warning(f"Request {i+1}: Rate limited! ({elapsed:.2f}s)")
                            retry_after = response.headers.get('Retry-After', 'unknown')
                            logger.warning(f"Retry-After: {retry_after}s")
                        else:
                            logger.error(f"Request {i+1}: Unexpected status {response.status}")
                            
                except Exception as e:
                    logger.error(f"Request {i+1}: Error - {str(e)}")
                
                # Small delay to make the output readable
                await asyncio.sleep(0.2)
            
            logger.info(f"\nRate limit test results:")
            logger.info(f"Successful requests: {success_count}")
            logger.info(f"Rate limited requests: {rate_limited_count}")
            
            # Wait for rate limit to reset
            logger.info("\nWaiting for rate limit to reset...")
            await asyncio.sleep(5)
            
            # Try one more request
            logger.info("Making one more request after waiting...")
            async with session.get(f"{server.url}/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=10") as response:
                if response.status == 200:
                    logger.info("Success! Rate limit has reset.")
                else:
                    logger.warning(f"Still rate limited: {response.status}")
        
    finally:
        # Clean up
        await server.stop()
        logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main())
```

## See Also

For more information about the mock server functionality, refer to:

- [Mock Server Documentation](../testing_resources/mock_server.md)
- [Exchange Simulation](../testing_resources/exchange_simulation.md)
- [Candle Data Factory](../testing_resources/candle_data_factory.md)
- [Testing Guide](../development/testing_guide.md)