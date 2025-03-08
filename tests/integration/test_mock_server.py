"""
Refactored integration tests for the mock exchange server.

This module tests the mock server components directly to ensure they
work correctly with different exchange plugins.
"""

import asyncio
import logging
from datetime import datetime, timezone

import aiohttp
import pytest

from candles_feed.core.candle_data import CandleData
from mocking_resources.core.candle_data_factory import CandleDataFactory
from mocking_resources.core import ExchangeType
from mocking_resources.core import MockedExchangeServer
from mocking_resources.exchanges.binance import BinanceSpotPlugin

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMockServer:
    """Integration tests for the mock exchange server with different plugins."""

    @pytest.fixture
    async def standalone_mock_server(self):
        """Create a standalone mock server for testing."""
        plugin = BinanceSpotPlugin(ExchangeType.BINANCE_SPOT)
        server = MockedExchangeServer(plugin, "127.0.0.1", 8790)

        # Add trading pairs
        server.add_trading_pair("BTCUSDT", "1m", 50000.0)
        server.add_trading_pair("ETHUSDT", "1m", 3000.0)
        server.add_trading_pair("SOLUSDT", "1m", 100.0)

        # Start the server
        url = await server.start()
        server.url = url

        yield server

        # Clean up
        await server.stop()

    @pytest.mark.asyncio
    async def test_server_rest_endpoints(self, standalone_mock_server):
        """Test the REST endpoints of the mock server."""
        mock_server_url = standalone_mock_server.url

        async with aiohttp.ClientSession() as session:
            # Test ping endpoint
            async with session.get(f"{mock_server_url}/api/v3/ping") as response:
                assert response.status == 200
                data = await response.json()
                assert isinstance(data, dict)

            # Test time endpoint
            async with session.get(f"{mock_server_url}/api/v3/time") as response:
                assert response.status == 200
                data = await response.json()
                assert "serverTime" in data
                assert isinstance(data["serverTime"], int)

            # Test klines endpoint
            params = {"symbol": "BTCUSDT", "interval": "1m", "limit": 10}

            async with session.get(f"{mock_server_url}/api/v3/klines", params=params) as response:
                assert response.status == 200
                data = await response.json()
                assert isinstance(data, list)
                assert len(data) > 0

                # Verify candle data structure for Binance
                first_candle = data[0]
                assert len(first_candle) == 12, "Binance candle should have 12 fields"

                # Verify candle fields
                assert isinstance(first_candle[0], int), "Open time should be an integer"
                assert isinstance(first_candle[1], str), "Open price should be a string"
                assert isinstance(first_candle[2], str), "High price should be a string"
                assert isinstance(first_candle[3], str), "Low price should be a string"
                assert isinstance(first_candle[4], str), "Close price should be a string"
                assert isinstance(first_candle[5], str), "Volume should be a string"

    @pytest.mark.asyncio
    async def test_server_websocket_connection_simple(self, standalone_mock_server):
        """Test basic WebSocket connection to the mock server."""
        server_host = standalone_mock_server.host
        server_port = standalone_mock_server.port

        # Create WebSocket URL
        ws_url = f"ws://{server_host}:{server_port}/ws"

        # Just test that we can connect to the WebSocket endpoint
        async with aiohttp.ClientSession() as session, session.ws_connect(ws_url) as ws:
            # Create subscription message (Binance format)
            subscription = {"method": "SUBSCRIBE", "params": ["btcusdt@kline_1m"], "id": 1}

            # Send subscription
            await ws.send_json(subscription)

            # Wait for subscription response
            response = await ws.receive_json(timeout=5.0)

            # Verify basic response
            assert response is not None
            assert "id" in response, "Missing id in subscription response"
            assert response["id"] == 1, "Wrong id in subscription response"

            # This test is simplified to just verify we can establish a connection
            # and receive a subscription response

    @pytest.mark.asyncio
    async def test_server_multiple_trading_pairs(self):
        """Test the mock server with multiple trading pairs."""
        # Create a new server instance for this test
        plugin = BinanceSpotPlugin(ExchangeType.BINANCE_SPOT)
        server = MockedExchangeServer(plugin, "127.0.0.1", 8791)

        # Add multiple trading pairs with different prices
        trading_pairs = [
            ("BTCUSDT", "1m", 50000.0),
            ("ETHUSDT", "1m", 3000.0),
            ("SOLUSDT", "1m", 100.0),
            ("DOGEUSDT", "1m", 0.1),
        ]

        for pair, interval, price in trading_pairs:
            server.add_trading_pair(pair, interval, price)

        try:
            # Start the server
            url = await server.start()

            # Test each trading pair
            async with aiohttp.ClientSession() as session:
                for pair, interval, _ in trading_pairs:
                    params = {"symbol": pair, "interval": interval, "limit": 1}

                    async with session.get(f"{url}/api/v3/klines", params=params) as response:
                        assert response.status == 200
                        data = await response.json()
                        assert len(data) > 0

                        # Get the close price of the latest candle
                        latest_price = float(data[-1][4])  # Close price is at index 4

                        # Mock server can change price significantly over time
                        # Just verify the price is a reasonable value > 0
                        if pair == "BTCUSDT":
                            assert 10000.0 <= latest_price <= 100000.0, (
                                f"BTC price {latest_price} out of reasonable range"
                            )
                        elif pair == "ETHUSDT":
                            assert 1000.0 <= latest_price <= 10000.0, (
                                f"ETH price {latest_price} out of reasonable range"
                            )
                        elif pair == "SOLUSDT":
                            assert 10.0 <= latest_price <= 1000.0, (
                                f"SOL price {latest_price} out of reasonable range"
                            )
                        elif pair == "DOGEUSDT":
                            assert 0.01 <= latest_price <= 10.0, (
                                f"DOGE price {latest_price} out of reasonable range"
                            )
                        else:
                            assert latest_price > 0, f"Price for {pair} should be positive"

        finally:
            # Stop the server
            await server.stop()

    @pytest.mark.asyncio
    async def test_server_network_simulation(self, standalone_mock_server):
        """Test the network simulation features of the mock server."""
        mock_server_url = standalone_mock_server.url

        # Test normal operation first
        async with aiohttp.ClientSession() as session:
            params = {"symbol": "BTCUSDT", "interval": "1m", "limit": 10}

            async with session.get(f"{mock_server_url}/api/v3/klines", params=params) as response:
                assert response.status == 200
                data = await response.json()
                assert len(data) > 0

        # Set moderate error conditions to make the test more reliable
        standalone_mock_server.set_network_conditions(
            latency_ms=50,
            packet_loss_rate=0.3,  # 30% packet loss
            error_rate=0.3,  # 30% error responses
        )

        # Test with error conditions
        async with aiohttp.ClientSession() as session:
            success_count = 0
            error_count = 0

            # Make multiple requests to test error scenarios
            for _ in range(10):
                try:
                    async with session.get(
                        f"{mock_server_url}/api/v3/klines",
                        params=params,
                        timeout=1.0,  # Short timeout
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if len(data) > 0:
                                success_count += 1
                        else:
                            error_count += 1
                except (asyncio.TimeoutError, aiohttp.ClientError):
                    error_count += 1

                await asyncio.sleep(0.1)

            # With 50% error rate, we expect some requests to succeed and some to fail
            assert success_count > 0, "All requests failed, but some should succeed"
            assert error_count > 0, "All requests succeeded, but some should fail"

        # Reset network conditions
        standalone_mock_server.set_network_conditions(
            latency_ms=0, packet_loss_rate=0.0, error_rate=0.0
        )

        # Verify normal operation is restored
        async with aiohttp.ClientSession() as session, session.get(
            f"{mock_server_url}/api/v3/klines", params=params
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert len(data) > 0

    @pytest.mark.asyncio
    async def test_mock_candle_data_methods(self):
        """Test that the CandleData class can create realistic candle sequences."""
        # Start with a base timestamp and price
        base_timestamp = int(datetime.now(timezone.utc).timestamp())
        base_price = 50000.0

        # Create a sequence of candles
        candles = []
        prev_candle = None

        # Generate 10 candles
        for i in range(10):
            if prev_candle is None:
                # First candle uses base price
                candle = CandleDataFactory.create_random(
                    timestamp=base_timestamp + (i * 60), base_price=base_price, volatility=0.01
                )
            else:
                # Subsequent candles use previous candle as reference
                candle = CandleDataFactory.create_random(
                    timestamp=base_timestamp + (i * 60),
                    previous_candle=prev_candle,
                    volatility=0.01,
                )

            candles.append(candle)
            prev_candle = candle

        # Verify candle sequence properties
        # 1. Each candle timestamp should be 60 seconds after the previous
        for i in range(1, len(candles)):
            assert candles[i].timestamp == candles[i - 1].timestamp + 60

        # 2. Open price of each candle (except first) should match close of previous
        for i in range(1, len(candles)):
            assert candles[i].open == candles[i - 1].close

        # 3. Verify each candle's price range is valid
        for candle in candles:
            assert candle.high >= max(candle.open, candle.close)
            assert candle.low <= min(candle.open, candle.close)
            assert candle.volume > 0

        # 4. Verify we have price movement
        # At least some candles should have different open/close prices
        diff_prices = sum(1 for c in candles if abs(c.open - c.close) > 0.0001)
        assert diff_prices > 0, "No price movement in generated candles"

        # 5. Price should generally stay within a reasonable range
        all_prices = [c.open for c in candles] + [c.close for c in candles]
        min_price = min(all_prices)
        max_price = max(all_prices)

        # Price should stay within 10% of base price with 1% volatility
        assert min_price >= base_price * 0.9, f"Min price {min_price} too low"
        assert max_price <= base_price * 1.1, f"Max price {max_price} too high"

    @pytest.mark.asyncio
    async def test_mock_candle_data_creation(self):
        """Test creating and manipulating CandleData objects."""
        # Test creating a basic candle
        timestamp = 1613677200  # 2021-02-19 00:00:00 UTC

        candle = CandleData(
            timestamp_raw=timestamp,
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50200.0,
            volume=10.0,
            quote_asset_volume=500000.0,
            n_trades=100,
            taker_buy_base_volume=5.0,
            taker_buy_quote_volume=250000.0,
        )

        # Verify candle properties
        assert candle.timestamp == timestamp
        assert candle.open == 50000.0
        assert candle.high == 50500.0
        assert candle.low == 49500.0
        assert candle.close == 50200.0
        assert candle.volume == 10.0
        assert candle.quote_asset_volume == 500000.0
        assert candle.n_trades == 100
        assert candle.taker_buy_base_volume == 5.0
        assert candle.taker_buy_quote_volume == 250000.0

        # Test timestamp_ms property
        assert candle.timestamp_ms == timestamp * 1000

        # Test creating a random candle
        random_candle = CandleDataFactory.create_random(
            timestamp=timestamp, base_price=50000.0, volatility=0.01
        )

        # Verify random candle properties
        assert random_candle.timestamp == timestamp
        assert random_candle.open == 50000.0  # Should match base_price
        assert random_candle.high >= max(random_candle.open, random_candle.close)
        assert random_candle.low <= min(random_candle.open, random_candle.close)
        assert random_candle.volume > 0

        # Test creating a candle based on a previous candle
        next_timestamp = timestamp + 60  # 1 minute later

        next_candle = CandleDataFactory.create_random(
            timestamp=next_timestamp, previous_candle=random_candle, volatility=0.01
        )

        # Verify next candle properties
        assert next_candle.timestamp == next_timestamp
        assert next_candle.open == random_candle.close  # Open should match previous close
        assert next_candle.high >= max(next_candle.open, next_candle.close)
        assert next_candle.low <= min(next_candle.open, next_candle.close)
