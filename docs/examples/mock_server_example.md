# Mock Server Example

This example demonstrates how to use the mock server framework for testing the Candles Feed library without connecting to real exchanges. This is particularly useful for development, testing, and CI/CD pipelines.

## Basic Server Setup

```python
import asyncio
import logging
from candles_feed.mocking_resources.core import ExchangeType
from candles_feed.mocking_resources.core import create_mock_server

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Example of setting up and using a mock exchange server."""
    # Create a mock server for Binance Spot
    server = create_mock_server(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host="127.0.0.1",
        port=8080
    )

    # Configure custom trading pairs
    custom_pairs = [
        ("BTC-USDT", "1m", 50000.0),  # BTC with initial price of $50,000
        ("ETH-USDT", "1m", 3000.0),  # ETH with initial price of $3,000
        ("SOL-USDT", "1m", 100.0),  # SOL with initial price of $100
        ("BTC-USDT", "5m", 50000.0),  # BTC with 5m interval
        ("BTC-USDT", "1h", 50000.0),  # BTC with 1h interval
    ]

    try:
        # Start the server
        await server.start()

        # Add custom trading pairs
        for symbol, interval, price in custom_pairs:
            server.add_trading_pair(symbol, interval, price)

        logger.info(f"Mock exchange server started at http://{server.host}:{server.port}")

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
from unittest.mock import patch
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.mocking_resources.core import ExchangeType
from candles_feed.mocking_resources.core import create_mock_server

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Example of using CandlesFeed with a mock server."""
    # Create and start a mock server
    server = create_mock_server(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host="127.0.0.1",
        port=8080
    )

    # Start the server with default trading pairs
    await server.start()
    server.add_trading_pair("BTC-USDT", "1m", 50000.0)

    logger.info(f"Mock server started at http://{server.host}:{server.port}")

    # Get the URL patching configuration from the plugin
    patched_urls = server.plugin.get_patched_urls(server.host, server.port)

    # Patch adapter URLs to point to our mock server
    with patch('candles_feed.adapters.binance.constants.SPOT_REST_URL', patched_urls["rest"]), \
         patch('candles_feed.adapters.binance.constants.SPOT_WSS_URL', patched_urls["ws"]):

        # Create a CandlesFeed instance
        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100
        )

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
                    logger.info(f"[WS Update {i + 1}] BTC price: {candles[-1].close}")

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
from unittest.mock import patch
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.mocking_resources.core import ExchangeType
from candles_feed.mocking_resources.core import create_mock_server

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Example of testing with difficult network conditions."""
    # Create and start a mock server
    server = create_mock_server(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host="127.0.0.1",
        port=8080
    )

    await server.start()
    server.add_trading_pair("BTC-USDT", "1m", 50000.0)
    logger.info(f"Mock server started at http://{server.host}:{server.port}")

    # Get the URL patching configuration from the plugin
    patched_urls = server.plugin.get_patched_urls(server.host, server.port)

    # Patch adapter URLs to point to our mock server
    with patch('candles_feed.adapters.binance.constants.SPOT_REST_URL', patched_urls["rest"]), \
         patch('candles_feed.adapters.binance.constants.SPOT_WSS_URL', patched_urls["ws"]):

        # Create a CandlesFeed instance
        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100
        )

        try:
            # First, get data with normal conditions
            logger.info("Fetching data with normal network conditions...")
            await feed.fetch_candles()
            normal_candles = len(feed.get_candles())
            logger.info(f"Received {normal_candles} candles")

            # Now simulate difficult network conditions
            logger.info("\nSetting difficult network conditions...")
            server.set_network_conditions(
                latency_ms=500,  # 500ms latency
                packet_loss_rate=0.3,  # 30% packet loss
                error_rate=0.3  # 30% error responses
            )

            # Try to fetch data under these conditions
            logger.info("Attempting to fetch data with difficult conditions...")
            success_count = 0
            error_count = 0

            for i in range(5):
                try:
                    logger.info(f"Attempt {i + 1}...")
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
import aiohttp
from candles_feed.mocking_resources.core import ExchangeType
from candles_feed.mocking_resources.core import create_mock_server

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Example of testing rate limiting."""
    # Create and start a mock server
    server = create_mock_server(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host="127.0.0.1",
        port=8080
    )

    await server.start()
    logger.info(f"Mock server started at http://{server.host}:{server.port}")

    # Access the rate limits from the plugin
    rate_limits = server.plugin.rate_limits

    # Override rate limits for testing
    rate_limits["rest"]["limit"] = 5  # Only 5 requests
    rate_limits["rest"]["period_ms"] = 5000  # Per 5 seconds
    rate_limits["ws"]["limit"] = 2  # 2 messages per second
    rate_limits["ws"]["burst"] = 3  # Burst of 3 allowed

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
                    url = f"http://{server.host}:{server.port}/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=10"
                    async with session.get(url) as response:
                        elapsed = time.time() - start_time

                        if response.status == 200:
                            success_count += 1
                            logger.info(f"Request {i + 1}: Success ({elapsed:.2f}s)")
                        elif response.status == 429:  # Too Many Requests
                            rate_limited_count += 1
                            logger.warning(f"Request {i + 1}: Rate limited! ({elapsed:.2f}s)")
                            retry_after = response.headers.get('Retry-After', 'unknown')
                            logger.warning(f"Retry-After: {retry_after}s")
                        else:
                            logger.error(f"Request {i + 1}: Unexpected status {response.status}")

                except Exception as e:
                    logger.error(f"Request {i + 1}: Error - {str(e)}")

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
            async with session.get(f"http://{server.host}:{server.port}/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=10") as response:
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

## Using with pytest-aiohttp

This example shows how to use the mock server with pytest-aiohttp:

```python
import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from unittest.mock import patch

from candles_feed.mocking_resources.core import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import BinanceSpotPlugin
from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter


@pytest_asyncio.fixture
async def binance_app():
    """Create a test application with the Binance plugin routes."""
    # Create the plugin
    plugin = BinanceSpotPlugin()

    # Create the aiohttp application
    app = web.Application()

    # Mock data for the server
    mock_data = {
        "candles": {
            "BTC-USDT": {
                "1m": []  # Will be filled with test data
            }
        },
        "trading_pairs": {"BTC-USDT": 50000.0}
    }

    # Generate some test candles
    from candles_feed.mocking_resources.core.candle_data_factory import CandleDataFactory
    factory = CandleDataFactory()
    mock_data["candles"]["BTC-USDT"]["1m"] = factory.generate_candles(
        trading_pair="BTC-USDT",
        interval="1m",
        num_candles=100,
        initial_price=50000.0
    )

    # Add plugin routes to app
    for route_path, (method, handler_name) in plugin.rest_routes.items():
        if hasattr(plugin, handler_name):
            handler = getattr(plugin, handler_name)

            # Create a wrapper that simulates the server object
            async def create_wrapper(handler):
                async def wrapper(request):
                    # Create a mock server object with required methods
                    mock_server = type('MockServer', (), {
                        '_simulate_network_conditions': lambda: None,
                        '_check_rate_limit': lambda client_ip, limit_type: True,
                        'candles': mock_data["candles"],
                        'trading_pairs': mock_data["trading_pairs"],
                        'last_candle_time': {},
                        '_time': lambda: 1613677200,  # Fixed time for tests
                        'verify_authentication': lambda request, required_permissions=None: {"authenticated": True, "error": None}
                    })()

                    return await handler(mock_server, request)
                return wrapper

            # Add route
            if method == "GET":
                app.router.add_get(route_path, await create_wrapper(handler))
            elif method == "POST":
                app.router.add_post(route_path, await create_wrapper(handler))

    return app


@pytest_asyncio.fixture
async def client(binance_app):
    """Create a test client for the application."""
    async with TestClient(TestServer(binance_app)) as client:
        yield client


@pytest_asyncio.fixture
async def adapter(client):
    """Create an adapter with URLs pointing to the test client."""
    adapter = BinanceSpotAdapter()

    # Get the server URL
    server_url = str(client.server.make_url(''))

    # Patch the adapter's URLs to point to our test server
    with patch('candles_feed.adapters.binance.constants.SPOT_REST_URL', server_url):
        yield adapter


@pytest.mark.asyncio
async def test_fetch_candles(client, adapter):
    """Test that we can fetch candles from the test server."""
    # Make a direct request to the klines endpoint
    response = await client.get("/api/v3/klines", params={
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 10
    })

    # Verify the response
    assert response.status == 200
    data = await response.json()
    assert isinstance(data, list)
    assert len(data) == 10

    # Test through the adapter
    candles = await adapter.fetch_rest_candles(
        trading_pair="BTC-USDT",
        interval="1m",
        limit=10
    )

    # Verify results
    assert len(candles) == 10
    for candle in candles:
        assert candle.timestamp is not None
        assert isinstance(candle.open, float)
        assert isinstance(candle.high, float)
```

## See Also

For more information about the mock server functionality, refer to:

- [Mock Server Documentation](../testing_resources/mock_server.md)
- [Testing Resources Overview](../testing_resources/overview.md)
