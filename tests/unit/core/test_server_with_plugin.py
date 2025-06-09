"""
Tests for the mock server with plugin-provided settings.

This test module demonstrates using pytest-aiohttp to test the mock server
with the refactored plugin framework that provides exchange-specific settings.
"""

import pytest
import pytest_asyncio

from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.server import MockedExchangeServer
from candles_feed.mocking_resources.core.url_patcher import ExchangeURLPatcher
from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import (
    BinanceSpotPlugin,
)


@pytest_asyncio.fixture
async def binance_server():
    """Fixture that provides a running Binance mock server instance."""
    # Create a Binance spot plugin
    plugin = BinanceSpotPlugin()

    # Create and start the server (use different port to avoid conflict with service containers)
    server = MockedExchangeServer(plugin, "127.0.0.1", 8081)

    # Add test trading pairs
    server.add_trading_pair("BTC-USDT", "1m", 50000.0)
    server.add_trading_pair("ETH-USDT", "1m", 3000.0)

    # Start the server
    await server.start()

    yield server

    # Clean up
    await server.stop()


@pytest_asyncio.fixture
async def client(aiohttp_client, binance_server):
    """Fixture that provides an aiohttp test client connected to the mock server."""
    # Create a test client for the server
    client = await aiohttp_client(binance_server.app)
    return client


@pytest.mark.asyncio
async def test_server_uses_plugin_rate_limits(client, binance_server):
    """Test that the server uses rate limits from the plugin."""
    # Get the rate limits from the server
    rate_limits = binance_server.rate_limits

    # Verify these match what we expect from the Binance plugin
    assert rate_limits["rest"]["limit"] == 1200
    assert rate_limits["rest"]["period_ms"] == 60000
    assert rate_limits["rest"]["weights"]["/api/v3/klines"] == 2

    # Test the rate limiting by making multiple requests
    for _ in range(5):
        response = await client.get(
            "/api/v3/klines", params={"symbol": "BTCUSDT", "interval": "1m"}
        )
        assert response.status == 200

    # The requests should not exceed the rate limit
    # You can use the MockedExchangeServer private methods to check this
    # but for now just assert the server is still responding
    response = await client.get("/api/v3/time")
    assert response.status == 200


@pytest.mark.asyncio
async def test_server_uses_plugin_api_keys(client, binance_server):
    """Test that the server uses API keys from the plugin."""
    # Get the API keys from the server
    api_keys = binance_server.api_keys

    # Verify these match what we expect from the Binance plugin
    assert "binance" in api_keys
    assert "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A" in api_keys["binance"]

    # Test authentication with a valid API key
    response = await client.get(
        "/api/v3/account",
        headers={
            "X-MBX-APIKEY": "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A"
        },
    )
    # Since we don't have the authentication logic implemented in this test,
    # just check that the server processed the request
    assert response.status != 401


@pytest.mark.asyncio
async def test_network_conditions_simulation(client, binance_server):
    """Test that the server can simulate network conditions."""
    # First test with no latency
    start_time = pytest.importorskip("time").time()
    response = await client.get("/api/v3/time")
    elapsed = pytest.importorskip("time").time() - start_time
    assert response.status == 200
    assert elapsed < 0.1  # Should be fast

    # Now set high latency
    binance_server.set_network_conditions(latency_ms=200)

    # Test again with latency
    start_time = pytest.importorskip("time").time()
    response = await client.get("/api/v3/time")
    elapsed = pytest.importorskip("time").time() - start_time
    assert response.status == 200
    assert elapsed >= 0.2  # Should be at least 200ms


@pytest.mark.asyncio
async def test_url_patcher(binance_server):
    """Test that the URL patcher works correctly."""
    # Create a URL patcher
    patcher = ExchangeURLPatcher(ExchangeType.BINANCE_SPOT, "127.0.0.1", 8081)

    # Patch the URLs
    success = patcher.patch_urls(binance_server.plugin)
    assert success

    # Test code would include verifying the URLs are patched correctly
    # by checking the adapter module directly or through the adapter behavior

    # Restore the URLs
    success = patcher.restore_urls()
    assert success
