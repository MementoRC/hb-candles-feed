"""
Example test demonstrating how to use aiohttp TestClient with the mock server framework.

This approach allows for easier testing of REST API endpoints without having to start 
actual servers and manage connections.
"""

import asyncio
import logging
from unittest.mock import patch

import pytest
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter

try:
    from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import BinanceSpotPlugin
except ImportError:
    # If not found, use the MockedPlugin as a fallback
    from candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin import MockedPlugin as BinanceSpotPlugin


# Setup the application with the plugin's routes
@pytest_asyncio.fixture
async def binance_app():
    """Create an aiohttp application with Binance routes."""
    # Create the plugin
    plugin = BinanceSpotPlugin()
    
    # Create the aiohttp application
    app = web.Application()
    
    # Add the plugin's REST routes to the application
    for route_path, (method, handler_name) in plugin.rest_routes.items():
        handler = getattr(plugin, handler_name)
        
        # Create a wrapper that passes the request to the handler
        # Note: We don't need the "server" parameter here as we're using TestClient
        async def create_wrapper(handler):
            async def wrapper(request):
                # Simulate server for the plugin handler
                async def dummy_simulate(self=None):
                    pass
                    
                mock_server = type('MockServer', (), {
                    '_simulate_network_conditions': dummy_simulate,
                    '_check_rate_limit': lambda self, client_ip, limit_type: True,
                    'verify_authentication': lambda self, request, required_permissions=None: {"authenticated": True, "error": None},
                    'candles': {},
                    'trading_pairs': {"BTC-USDT": 50000.0, "ETH-USDT": 3000.0},
                    'last_candle_time': {},
                    '_time': lambda self=None: asyncio.get_running_loop().time(),
                    'logger': logging.getLogger(__name__)
                })()
                
                # Generate some test candles for BTC-USDT
                from candles_feed.mocking_resources.core.candle_data_factory import CandleDataFactory
                import time
                
                # Create a list of candles manually
                candles = []
                base_time = int(time.time())
                
                # Create 100 candles 1 minute apart
                for i in range(100):
                    timestamp = base_time - (99 - i) * 60  # Oldest to newest
                    candle = CandleDataFactory.create_random(
                        timestamp=timestamp,
                        base_price=50000.0,
                        volatility=0.01
                    )
                    candles.append(candle)
                
                # Add candles to mock server
                # Generate ETH candles manually too
                eth_candles = []
                for i in range(100):
                    timestamp = base_time - (99 - i) * 300  # 5 minute intervals
                    eth_candle = CandleDataFactory.create_random(
                        timestamp=timestamp,
                        base_price=3000.0,
                        volatility=0.01
                    )
                    eth_candles.append(eth_candle)
                
                mock_server.candles = {
                    "BTC-USDT": {"1m": candles},
                    "ETH-USDT": {"5m": eth_candles}
                }
                
                # Add last candle times
                mock_server.last_candle_time = {
                    "BTC-USDT": {"1m": candles[-1].timestamp_ms},
                    "ETH-USDT": {"5m": eth_candles[-1].timestamp_ms}
                }
                
                return await handler(mock_server, request)
            return wrapper
        
        # Add the route to the application
        if method == "GET":
            app.router.add_get(route_path, await create_wrapper(handler))
        elif method == "POST":
            app.router.add_post(route_path, await create_wrapper(handler))
        elif method == "PUT":
            app.router.add_put(route_path, await create_wrapper(handler))
        elif method == "DELETE":
            app.router.add_delete(route_path, await create_wrapper(handler))
    
    return app


# Create a test client fixture
@pytest_asyncio.fixture
async def client(binance_app):
    """Create a test client for the Binance application."""
    async with TestClient(TestServer(binance_app)) as client:
        yield client


# Create adapter with patched URLs
@pytest_asyncio.fixture
async def spot_adapter(client):
    """Create a spot adapter with patched URLs pointing to the test client."""
    # Create a network client for the adapter
    from candles_feed.core.network_client import NetworkClient
    network_client = NetworkClient()
    
    adapter = BinanceSpotAdapter()
    
    # Patch the URLs to point to the test client
    server_url = str(client.server.make_url(''))
    
    with patch('candles_feed.adapters.binance.constants.SPOT_REST_URL', server_url):
        yield adapter, network_client
        
    # Clean up
    await network_client.close()


# Test cases
@pytest.mark.asyncio
async def test_ping_endpoint(client):
    """Test the ping endpoint."""
    # Send a request to the ping endpoint
    response = await client.get("/api/v3/ping")
    
    # Check the response
    assert response.status == 200
    data = await response.json()
    assert data == {}


@pytest.mark.asyncio
async def test_time_endpoint(client):
    """Test the time endpoint."""
    # Send a request to the time endpoint
    response = await client.get("/api/v3/time")
    
    # Check the response
    assert response.status == 200
    data = await response.json()
    assert "serverTime" in data
    assert isinstance(data["serverTime"], int)


@pytest.mark.asyncio
async def test_klines_endpoint(client):
    """Test the klines endpoint."""
    # Send a request to the klines endpoint
    response = await client.get("/api/v3/klines", params={
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 10
    })
    
    # Check the response
    assert response.status == 200
    data = await response.json()
    
    # Verify the data structure
    assert isinstance(data, list)
    assert len(data) == 10  # We requested 10 candles
    
    # Check the candle structure
    for candle in data:
        assert len(candle) == 12  # Binance candles have 12 fields
        assert isinstance(candle[0], int)  # Open time
        assert isinstance(candle[1], str)  # Open price
        assert isinstance(candle[2], str)  # High price
        assert isinstance(candle[3], str)  # Low price
        assert isinstance(candle[4], str)  # Close price
        assert isinstance(candle[5], str)  # Volume


@pytest.mark.asyncio
async def test_error_handling(client):
    """Test error handling for invalid parameters."""
    # Send a request with an invalid symbol
    response = await client.get("/api/v3/klines", params={
        "symbol": "INVALID",
        "interval": "1m",
        "limit": 10
    })
    
    # Check that we get an error response
    assert response.status == 400
    error = await response.json()
    assert "code" in error
    assert "msg" in error
    assert "invalid" in error["msg"].lower() or "symbol" in error["msg"].lower()
    
    # Send a request with an invalid interval
    response = await client.get("/api/v3/klines", params={
        "symbol": "BTCUSDT",
        "interval": "invalid",
        "limit": 10
    })
    
    # Check that we get an error response
    assert response.status == 400
    error = await response.json()
    assert "code" in error
    assert "msg" in error
    assert "interval" in error["msg"].lower()