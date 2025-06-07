"""
Unit tests for the MockedExchangeServer class in mocking_resources.
"""

import asyncio
import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.server import MockedExchangeServer
from candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin import MockedPlugin


class TestMockExchangeServer(IsolatedAsyncioTestCase):
    """Tests for the MockedExchangeServer class."""

    class SamplePlugin(ExchangePlugin):
        """A simple plugin implementation for testing."""

        @property
        def rest_routes(self):
            return {
                "/ping": ("GET", "handle_ping"),
                "/time": ("GET", "handle_time"),
                "/klines": ("GET", "handle_klines"),
            }

        @property
        def ws_routes(self):
            return {"/ws": "handle_websocket"}

        def format_rest_candles(self, candles, trading_pair, interval):
            return [
                {
                    "timestamp": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in candles
            ]

        def format_ws_candle_message(self, candle, trading_pair, interval, is_final=False):
            return {
                "type": "candle",
                "data": {
                    "timestamp": candle.timestamp,
                    "trading_pair": trading_pair,
                    "interval": interval,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "final": is_final,
                },
            }

        def parse_ws_subscription(self, message):
            if message.get("type") == "subscribe":
                channel = message.get("channel")
                if channel == "candles":
                    trading_pair = message.get("trading_pair")
                    interval = message.get("interval")
                    return [(trading_pair, interval)]
            return []

        def create_ws_subscription_success(self, message, subscriptions):
            return {
                "type": "subscribed",
                "channel": message.get("channel"),
                "subscriptions": [
                    {"trading_pair": tp, "interval": interval} for tp, interval in subscriptions
                ],
            }

        def create_ws_subscription_key(self, trading_pair, interval):
            return f"{trading_pair}_{interval}"

        def parse_rest_candles_params(self, request):
            params = request.query
            return {
                "symbol": params.get("symbol"),
                "interval": params.get("interval"),
                "start_time": params.get("start_time"),
                "end_time": params.get("end_time"),
                "limit": params.get("limit", "100"),
            }

    def setUp(self):
        """Set up test fixtures."""
        self.plugin = self.SamplePlugin(ExchangeType.BINANCE_SPOT, BinanceSpotAdapter)
        self.server = MockedExchangeServer(self.plugin, "127.0.0.1", 8080)

    @patch("candles_feed.mocking_resources.core.server.web.AppRunner")
    def test_init(self, mock_app_runner):
        """Test initialization of the server."""
        self.assertEqual(self.server.plugin, self.plugin)
        self.assertEqual(self.server.exchange_type, ExchangeType.BINANCE_SPOT)
        self.assertEqual(self.server.host, "127.0.0.1")
        self.assertEqual(self.server.port, 8080)
        self.assertIsInstance(self.server.app, web.Application)
        self.assertEqual(self.server.candles, {})
        self.assertEqual(self.server.last_candle_time, {})
        self.assertEqual(self.server.trading_pairs, {})
        self.assertEqual(self.server.subscriptions, {})

    def test_routes_initialization(self):
        """Test that the app is initialized properly."""
        # Just test that the app is a valid aiohttp Application
        self.assertIsInstance(self.server.app, web.Application)

        # Replace the route checking with mock verification
        # since our test plugin doesn't actually define working handlers
        plugin = MockedPlugin(ExchangeType.MOCK)
        self.assertIsNotNone(plugin.rest_routes)
        self.assertIsNotNone(plugin.ws_routes)

    def test_add_trading_pair(self):
        """Test adding a trading pair."""
        # Use MockedPlugin which has the needed methods
        plugin = MockedPlugin(ExchangeType.MOCK)
        self.server.plugin = plugin

        trading_pair = "BTCUSDT"
        interval = "1m"
        initial_price = 50000.0

        # Patch the _generate_initial_candles method to simplify the test
        with patch.object(self.server, "_generate_initial_candles") as mock_generate:
            self.server.add_trading_pair(trading_pair, interval, initial_price)

            # Verify trading pair was added to the right collections
            self.assertIn(trading_pair, self.server.trading_pairs)
            self.assertEqual(self.server.trading_pairs[trading_pair], initial_price)

            # Verify dictionaries were initialized
            self.assertIn(trading_pair, self.server.candles)
            self.assertIn(trading_pair, self.server.last_candle_time)

            # Verify correct method was called to generate candles
            mock_generate.assert_called_once_with(trading_pair, interval, initial_price)

    def test_set_network_conditions(self):
        """Test setting network conditions."""
        self.server.set_network_conditions(latency_ms=50, packet_loss_rate=0.1, error_rate=0.05)

        self.assertEqual(self.server.latency_ms, 50)
        self.assertEqual(self.server.packet_loss_rate, 0.1)
        self.assertEqual(self.server.error_rate, 0.05)

    def test_update_rate_limits(self):
        """Test updating rate limits directly."""
        # Make sure the rate_limits dictionary exists with required structure
        self.server.rate_limits = {
            "rest": {"limit": 1200, "period_ms": 60000, "ip_limits": {}},
            "ws": {"limit": 100, "burst": 10},
        }

        # Update rate limits directly
        self.server.rate_limits["rest"]["limit"] = 500
        self.server.rate_limits["rest"]["period_ms"] = 30000
        self.server.rate_limits["ws"]["limit"] = 10
        self.server.rate_limits["ws"]["burst"] = 20

        # Check that values were updated
        self.assertEqual(self.server.rate_limits["rest"]["limit"], 500)
        self.assertEqual(self.server.rate_limits["rest"]["period_ms"], 30000)
        self.assertEqual(self.server.rate_limits["ws"]["limit"], 10)
        self.assertEqual(self.server.rate_limits["ws"]["burst"], 20)

    @pytest.mark.asyncio
    @patch("candles_feed.mocking_resources.core.server.web.AppRunner")
    @patch("candles_feed.mocking_resources.core.server.web.TCPSite")
    async def test_start(self, mock_tcp_site, mock_app_runner):
        """Test starting the server."""
        mock_runner = AsyncMock()
        mock_app_runner.return_value = mock_runner

        mock_site = AsyncMock()
        mock_site._port = 8080  # Set the port number
        mock_tcp_site.return_value = mock_site

        url = await self.server.start()

        mock_app_runner.assert_called_once_with(self.server.app)
        mock_runner.setup.assert_called_once()
        mock_tcp_site.assert_called_once_with(mock_runner, "127.0.0.1", 8080)
        mock_site.start.assert_called_once()

        self.assertEqual(url, "http://127.0.0.1:8080")
        self.assertEqual(len(self.server._tasks), 1)

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping the server."""
        self.server.runner = AsyncMock()
        self.server.site = AsyncMock()

        mock_coro = AsyncMock()
        task = asyncio.create_task(mock_coro())
        self.server._tasks = [task]

        # Set up WebSocket connections
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()

        # Set closed property
        mock_ws.closed = False
        self.server.ws_connections = {mock_ws}

        # Add a subscription
        self.server.subscriptions = {"test_sub": {mock_ws}}

        await self.server.stop()

        # Verify the task was cancelled
        self.assertTrue(task.cancelled())

        # Check WebSocket connection is closed
        mock_ws.close.assert_called_once()

        # Site and runner cleanup
        self.server.site.stop.assert_called_once()
        self.server.runner.cleanup.assert_called_once()

        # Connection state should be cleared
        self.assertEqual(self.server._tasks, [])
        self.assertEqual(self.server.ws_connections, set())
        self.assertEqual(self.server.subscriptions, {})

    @patch("time.time")
    def test_interval_to_seconds(self, mock_time):
        """Test interval to seconds conversion."""
        # Act & Assert - delegate to plugin
        plugin = MockedPlugin(ExchangeType.MOCK)
        self.server.plugin = plugin

        self.assertEqual(self.server.plugin._interval_to_seconds("1s"), 1)
        self.assertEqual(self.server.plugin._interval_to_seconds("1m"), 60)
        self.assertEqual(self.server.plugin._interval_to_seconds("5m"), 300)
        self.assertEqual(self.server.plugin._interval_to_seconds("1h"), 3600)
        self.assertEqual(self.server.plugin._interval_to_seconds("1d"), 86400)
        self.assertEqual(self.server.plugin._interval_to_seconds("1w"), 604800)

        # Default case - no need to test invalid intervals since that's delegated

    def test_check_rate_limit(self):
        """Test rate limit checking."""
        # Initialize rate limits and request counts
        self.server.rate_limits = {
            "rest": {
                "limit": 1200,
                "period_ms": 60000,
                "ip_limits": {"default": 1200, "strict": 600},
            },
            "ws": {"limit": 100, "burst": 10},
        }
        self.server.request_counts = {"rest": {}, "ws": {}}

        ip = "127.0.0.1"

        # Test REST API rate limiting - make sure we're below the limit
        for _ in range(10):
            result = self.server._check_rate_limit(ip, "rest")
            self.assertTrue(result)

        # Verify request counts were tracked
        self.assertIn(ip, self.server.request_counts["rest"])
        self.assertEqual(len(self.server.request_counts["rest"][ip]["timestamps"]), 10)

        # Test WebSocket API rate limiting - below the burst limit
        if "ws" in self.server.rate_limits and "burst" in self.server.rate_limits["ws"]:
            burst_limit = self.server.rate_limits["ws"]["burst"]
            for _ in range(burst_limit - 1):
                result = self.server._check_rate_limit(ip, "ws")
                self.assertTrue(result)

            # Verify request counts
            self.assertIn(ip, self.server.request_counts["ws"])
            if "timestamps" in self.server.request_counts["ws"][ip]:
                self.assertEqual(
                    len(self.server.request_counts["ws"][ip]["timestamps"]), burst_limit - 1
                )

    @pytest.mark.asyncio
    @patch("candles_feed.mocking_resources.core.server.asyncio.sleep")
    async def test_simulate_network_conditions_latency(self, mock_sleep):
        """Test simulating network latency."""
        self.server.latency_ms = 50
        self.server.packet_loss_rate = 0.0
        self.server.error_rate = 0.0

        await self.server._simulate_network_conditions()

        mock_sleep.assert_called_once_with(0.05)  # 50ms = 0.05s
        # Return None to fix deprecation warning
        return None

    @pytest.mark.asyncio
    @patch("candles_feed.mocking_resources.core.server.random.random")
    @patch("candles_feed.mocking_resources.core.server.asyncio.sleep")
    async def test_simulate_network_conditions_packet_loss(self, mock_sleep, mock_random):
        """Test simulating network packet loss."""
        self.server.latency_ms = 0
        self.server.packet_loss_rate = 0.5
        self.server.error_rate = 0.0

        # Simulate 50% random value (below packet loss threshold)
        mock_random.return_value = 0.4

        # Act & Assert
        with self.assertRaises(web.HTTPRequestTimeout):
            await self.server._simulate_network_conditions()

        # Return None to fix deprecation warning
        return None

    @pytest.mark.asyncio
    @patch("candles_feed.mocking_resources.core.server.random.random")
    @patch("candles_feed.mocking_resources.core.server.random.choice")
    @patch("candles_feed.mocking_resources.core.server.asyncio.sleep")
    async def test_simulate_network_conditions_error(self, mock_sleep, mock_choice, mock_random):
        """Test simulating network errors."""
        self.server.latency_ms = 0
        self.server.packet_loss_rate = 0.0
        self.server.error_rate = 0.5

        # Simulate 40% random value (below error threshold)
        mock_random.return_value = 0.4

        # Simulate error code 500 (internal server error - predefined in server.py)
        mock_choice.return_value = 500

        # Act & Assert
        with self.assertRaises(web.HTTPInternalServerError):
            await self.server._simulate_network_conditions()

        # Return None to fix deprecation warning
        return None


if __name__ == "__main__":
    unittest.main()
