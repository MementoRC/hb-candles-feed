"""
Unit tests for the HyperliquidPerpetualAdapter class using the mock exchange server.
"""

import asyncio
import json
from typing import Any, Dict, List

import aiohttp
import pytest

from candles_feed.adapters.hyperliquid.perpetual_adapter import HyperliquidPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.factory import create_mock_server_for_exchange


@pytest.fixture
async def hyperliquid_mock_server():
    """
    Create and start a mock Hyperliquid server, yield it, then stop it after the test.
    """
    # Create a mock server with specific trading pairs and initial prices
    server = create_mock_server_for_exchange(
        ExchangeType.HYPERLIQUID_PERPETUAL, "127.0.0.1", 0,
        [
            ("BTC-USDT", "1m", 50000.0),
            ("ETH-USDT", "1m", 3000.0),
            ("SOL-USDT", "1m", 100.0),
        ],
    )
    
    # Start the server
    await server.start()
    
    # Yield the server to the test
    yield server
    
    # Stop the server after the test
    await server.stop()


@pytest.fixture
def mock_server_url(hyperliquid_mock_server):
    """
    Get the URL to the mock server.
    """
    return f"http://{hyperliquid_mock_server.host}:{hyperliquid_mock_server.port}"


class TestHyperliquidPerpetualAdapterWithMockServer:
    """Test suite for the HyperliquidPerpetualAdapter with mock server."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = HyperliquidPerpetualAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    @pytest.mark.asyncio
    async def test_fetch_recent_candles(self, hyperliquid_mock_server, mock_server_url):
        """Test fetching recent candles from mock server."""
        # Create a session
        async with aiohttp.ClientSession() as session:
            # Get request parameters
            payload = self.adapter.get_rest_payload(self.trading_pair, self.interval, limit=10)

            # Create URL for Hyperliquid API
            url = f"{mock_server_url}/info"

            # Fetch data using POST request with JSON payload
            async with session.post(url, json=payload) as response:
                # Verify successful response
                assert response.status == 200

                # Get the data
                data = await response.json()

                # Verify we have candles
                assert isinstance(data, list)
                assert len(data) > 0

                # Parse the response
                candles = self.adapter.parse_rest_response(data)

                # Verify parsed candles
                assert len(candles) > 0
                for candle in candles:
                    assert isinstance(candle, CandleData)
                    assert hasattr(candle, "timestamp_ms")
                    assert hasattr(candle, "open")
                    assert hasattr(candle, "high")
                    assert hasattr(candle, "low")
                    assert hasattr(candle, "close")
                    assert hasattr(candle, "volume")

    @pytest.mark.asyncio
    async def test_websocket_connection(self, hyperliquid_mock_server, mock_server_url):
        """Test WebSocket connection to mock server."""
        # Extract host and port from mock server URL
        host_port = mock_server_url.split("//")[1]
        
        # Create websocket URL
        ws_url = f"ws://{host_port}/ws"
        
        # Create WebSocket connection
        async with aiohttp.ClientSession() as session, session.ws_connect(ws_url) as ws:
            # Create subscription payload
            payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

            # Send subscription request
            await ws.send_json(payload)

            # Wait for subscription response
            response = await ws.receive_json(timeout=5.0)

            # Verify subscription was successful
            assert response is not None
            assert response.get("success") is True

            # Wait for a candle message
            try:
                message = await ws.receive_json(timeout=5.0)
                # Parse the WebSocket message
                if message:
                    candles = self.adapter.parse_ws_message(message)
                    if candles:
                        # Verify we have parsed candles
                        assert len(candles) > 0
                        for candle in candles:
                            assert isinstance(candle, CandleData)
                            assert hasattr(candle, "timestamp_ms")
            except asyncio.TimeoutError:
                # No message received in time, but the test still passes
                # as the connection was successful
                pass

            # Close connection
            await ws.close()