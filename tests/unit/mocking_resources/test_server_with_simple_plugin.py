"""
Tests for the MockedExchangeServer with MockedPlugin.
"""

import asyncio
import json

import aiohttp
import pytest

from candles_feed.mocking_resources.core import MockedExchangeServer
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin import MockedPlugin


class TestServerWithSimplePlugin:
    """Test the MockedExchangeServer with MockedPlugin."""

    @pytest.mark.asyncio
    async def test_server_initialization(self, unused_tcp_port):
        """Test server initialization with MockedPlugin."""
        # Create server with MockedPlugin
        plugin = MockedPlugin()
        server = MockedExchangeServer(plugin, "127.0.0.1", unused_tcp_port)

        # Add a trading pair
        server.add_trading_pair("BTC-USDT", "1m", 50000.0)

        # Start the server
        url = await server.start()

        # Verify server starts successfully
        assert url is not None
        assert url.startswith("http://")

        # Clean up
        await server.stop()

    @pytest.mark.asyncio
    async def test_rest_candles_endpoint(self, unused_tcp_port):
        """Test the REST candles endpoint."""
        # Create server with MockedPlugin
        plugin = MockedPlugin()
        server = MockedExchangeServer(plugin, "127.0.0.1", unused_tcp_port)

        # Add trading pairs
        server.add_trading_pair("BTC-USDT", "1m", 50000.0)
        server.add_trading_pair("ETH-USDT", "1m", 3000.0)

        # Start the server
        url = await server.start()

        # Create client session
        async with aiohttp.ClientSession() as session:
            # Make request to candles endpoint
            async with session.get(
                f"{url}/api/candles",
                params={"symbol": "BTC-USDT", "interval": "1m", "limit": 10}
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

                # Verify candles are generated
                assert len(data["data"]) > 0

                # Check a candle
                candle = data["data"][0]
                assert "timestamp" in candle
                assert "open" in candle
                assert "high" in candle
                assert "low" in candle
                assert "close" in candle
                assert "volume" in candle

                # Verify the price is around the initial price
                assert abs(float(candle["close"]) - 50000.0) < 5000.0  # Allow some variation

        # Clean up
        await server.stop()

    @pytest.mark.asyncio
    async def test_websocket_connection(self, unused_tcp_port):
        """Test WebSocket connection and subscription."""
        # Create server with MockedPlugin
        plugin = MockedPlugin()
        server = MockedExchangeServer(plugin, "127.0.0.1", unused_tcp_port)

        # Add trading pairs
        server.add_trading_pair("BTC-USDT", "1m", 50000.0)

        # Start the server
        await server.start()

        # Get WebSocket URL
        ws_url = f"ws://127.0.0.1:{unused_tcp_port}/ws"

        # Create WebSocket connection
        async with aiohttp.ClientSession() as session, session.ws_connect(ws_url) as ws:
            # Send subscription message
            await ws.send_json({
                "type": "subscribe",
                "subscriptions": [
                    {
                        "symbol": "BTC-USDT",
                        "interval": "1m"
                    }
                ]
            })

            # Wait for subscription response
            response = await ws.receive_json(timeout=5)

            # Verify subscription response
            assert "type" in response
            assert response["type"] == "subscribe_result"
            assert "status" in response
            assert response["status"] == "success"

            # Wait for candle update (might timeout if no immediate update)
            try:
                update = await asyncio.wait_for(ws.receive_json(), timeout=2)

                # If we got an update, verify its structure
                if "type" in update and update["type"] == "candle_update":
                    assert "symbol" in update
                    assert update["symbol"] == "BTC-USDT"
                    assert "interval" in update
                    assert update["interval"] == "1m"
                    assert "data" in update
                    assert "timestamp" in update["data"]
                    assert "open" in update["data"]
                    assert "high" in update["data"]
                    assert "low" in update["data"]
                    assert "close" in update["data"]
                    assert "volume" in update["data"]
            except asyncio.TimeoutError:
                # It's okay if we don't get an update in this short timeframe
                pass

        # Clean up
        await server.stop()

    @pytest.mark.asyncio
    async def test_multiple_trading_pairs(self, unused_tcp_port):
        """Test handling multiple trading pairs."""
        # Create server with MockedPlugin
        plugin = MockedPlugin()
        server = MockedExchangeServer(plugin, "127.0.0.1", unused_tcp_port)

        # Add multiple trading pairs
        server.add_trading_pair("BTC-USDT", "1m", 50000.0)
        server.add_trading_pair("ETH-USDT", "1m", 3000.0)
        server.add_trading_pair("SOL-USDT", "1m", 100.0)

        # Start the server
        url = await server.start()

        # Create client session
        async with aiohttp.ClientSession() as session:
            # Check BTC-USDT candles
            async with session.get(
                f"{url}/api/candles",
                params={"symbol": "BTC-USDT", "interval": "1m", "limit": 5}
            ) as response:
                data = await response.json()
                assert data["symbol"] == "BTC-USDT"
                assert len(data["data"]) > 0
                assert abs(float(data["data"][0]["close"]) - 50000.0) < 5000.0

            # Check ETH-USDT candles
            async with session.get(
                f"{url}/api/candles",
                params={"symbol": "ETH-USDT", "interval": "1m", "limit": 5}
            ) as response:
                data = await response.json()
                assert data["symbol"] == "ETH-USDT"
                assert len(data["data"]) > 0
                assert abs(float(data["data"][0]["close"]) - 3000.0) < 300.0

            # Check SOL-USDT candles
            async with session.get(
                f"{url}/api/candles",
                params={"symbol": "SOL-USDT", "interval": "1m", "limit": 5}
            ) as response:
                data = await response.json()
                assert data["symbol"] == "SOL-USDT"
                assert len(data["data"]) > 0
                assert abs(float(data["data"][0]["close"]) - 100.0) < 10.0

        # Clean up
        await server.stop()

    @pytest.mark.asyncio
    async def test_time_endpoint(self, unused_tcp_port):
        """Test the time endpoint."""
        # Create server with MockedPlugin
        plugin = MockedPlugin()
        server = MockedExchangeServer(plugin, "127.0.0.1", unused_tcp_port)

        # Start the server
        url = await server.start()

        # Create client session
        async with aiohttp.ClientSession() as session:
            # Make request to time endpoint
            async with session.get(f"{url}/api/time") as response:
                # Check response
                assert response.status == 200
                data = await response.json()

                # Verify response format
                assert "status" in data
                assert data["status"] == "ok"
                assert "timestamp" in data
                assert "server_time" in data

                # Verify time is current
                current_time = server._time()
                server_time = data["timestamp"] / 1000  # Convert from ms to seconds

                # Allow a small time difference
                assert abs(current_time - server_time) < 60

        # Clean up
        await server.stop()

    @pytest.mark.asyncio
    async def test_instruments_endpoint(self, unused_tcp_port):
        """Test the instruments endpoint."""
        # Create server with MockedPlugin
        plugin = MockedPlugin()
        server = MockedExchangeServer(plugin, "127.0.0.1", unused_tcp_port)

        # Add trading pairs
        server.add_trading_pair("BTC-USDT", "1m", 50000.0)
        server.add_trading_pair("ETH-USDT", "1m", 3000.0)

        # Start the server
        url = await server.start()

        # Create client session
        async with aiohttp.ClientSession() as session:
            # Make request to instruments endpoint
            async with session.get(f"{url}/api/instruments") as response:
                # Check response
                assert response.status == 200
                data = await response.json()

                # Verify response format
                assert "status" in data
                assert data["status"] == "ok"
                assert "instruments" in data
                assert isinstance(data["instruments"], list)

                # Verify instruments
                assert len(data["instruments"]) == 2

                # Check if both trading pairs are in the response
                instrument_symbols = [instr["symbol"] for instr in data["instruments"]]
                assert "BTC-USDT" in instrument_symbols
                assert "ETH-USDT" in instrument_symbols

                # Check instrument structure
                for instrument in data["instruments"]:
                    assert "symbol" in instrument
                    assert "base_asset" in instrument
                    assert "quote_asset" in instrument
                    assert "status" in instrument
                    assert instrument["status"] == "TRADING"

        # Clean up
        await server.stop()
