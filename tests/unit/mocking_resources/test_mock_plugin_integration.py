"""
Tests the integration of the MockedPlugin with the MockedExchangeServer.
"""

import asyncio

import aiohttp
import pytest

from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.factory import get_plugin
from candles_feed.mocking_resources.core.server import MockedExchangeServer


@pytest.mark.integration
class TestMockPluginIntegration:
    """Test the MockedPlugin integration with MockedExchangeServer."""

    @pytest.mark.asyncio
    async def test_server_start(self, unused_tcp_port):
        """Test starting the server with the mock plugin."""
        # Get the mock plugin
        plugin = get_plugin(ExchangeType.MOCK)

        # Create server with mock plugin
        server = MockedExchangeServer(plugin, "127.0.0.1", unused_tcp_port)

        # Add trading pairs
        trading_pairs = [
            ("BTC-USDT", "1m", 50000.0),
            ("ETH-USDT", "1m", 3000.0),
        ]

        for symbol, interval, price in trading_pairs:
            server.add_trading_pair(symbol, interval, price)

        # Start server
        url = await server.start()

        # Verify server started correctly
        assert url is not None

        # Clean up
        await server.stop()

    @pytest.mark.asyncio
    async def test_rest_candles_endpoint(self, mocked_server_fixture):
        """Test the REST API candles endpoint."""
        url = mocked_server_fixture.mocked_exchange_url

        # Create client session
        async with aiohttp.ClientSession() as session, session.get(
            f"{url}/api/candles?symbol=BTC-USDT&interval=1m&limit=10"
        ) as response:
            # Check response
            assert response.status == 200
            data = await response.json()

            # Verify response format
            assert "status" in data
            assert data["status"] == "ok"
            assert "symbol" in data
            assert data["symbol"] == "BTC-USDT"
            assert "interval" in data
            assert data["interval"] == "1m"
            assert "data" in data
            assert isinstance(data["data"], list)

            # Verify at least one candle is returned
            assert len(data["data"]) > 0

            # Verify candle structure
            candle = data["data"][0]
            assert "timestamp" in candle
            assert "open" in candle
            assert "high" in candle
            assert "low" in candle
            assert "close" in candle
            assert "volume" in candle

    @pytest.mark.asyncio
    async def test_websocket_connection(self, mocked_server_fixture):
        """Test WebSocket connection and subscription."""
        url = mocked_server_fixture.mocked_exchange_url
        ws_url = f"ws://{url.split('://')[-1]}/ws"

        # Create WebSocket session
        async with aiohttp.ClientSession() as session, session.ws_connect(ws_url) as ws:
            # Send subscription message
            subscription_message = {
                "type": "subscribe",
                "subscriptions": [{"symbol": "BTC-USDT", "interval": "1m"}],
            }
            await ws.send_json(subscription_message)

            # Wait for subscription response
            response = await ws.receive_json(timeout=5)

            # Verify subscription response
            assert "type" in response
            assert response["type"] == "subscribe_result"
            assert "status" in response
            assert response["status"] == "success"

            # Wait briefly for potential candle updates
            try:
                update = await asyncio.wait_for(ws.receive_json(), timeout=2)

                # If we got an update, verify its structure
                if "type" in update and update["type"] == "candle_update":
                    assert "symbol" in update
                    assert "interval" in update
                    assert "data" in update
            except asyncio.TimeoutError:
                # It's okay if we don't get an update in this short timeframe
                pass
