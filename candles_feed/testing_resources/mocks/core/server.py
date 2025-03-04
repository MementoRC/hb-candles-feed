"""
Core mock exchange server implementation.
"""

import asyncio
import contextlib
import json
import logging
import random
import time
from collections import deque
from typing import TYPE_CHECKING

import aiohttp
from aiohttp import web

from candles_feed.core.candle_data import CandleData
from candles_feed.testing_resources.candle_data_factory import CandleDataFactory
from candles_feed.testing_resources.mocks.core.exchange_plugin import ExchangePlugin

if TYPE_CHECKING:
    from candles_feed.testing_resources.mocks import ExchangeType


class MockExchangeServer:
    """
    Configurable mock server for cryptocurrency exchange API simulation.

    This server provides REST and WebSocket endpoints that simulate
    the behavior of various exchanges for testing purposes.
    """

    def __init__(self, plugin: ExchangePlugin, host: str = "127.0.0.1", port: int = 8080):
        """
        Initialize the mock exchange server.

        Args:
            plugin: The exchange plugin to use for exchange-specific behavior
            host: Host to bind the server to
            port: Port to bind the server to
        """
        self.plugin: ExchangePlugin = plugin
        self.exchange_type: ExchangeType = plugin.exchange_type
        self.host: str = host
        self.port: int = port
        self.app: web.Application = web.Application()
        self.runner = None
        self.site = None
        self.logger: logging.Logger = logging.getLogger(__name__)

        # Server state
        self.candles: dict[
            str, dict[str, list[CandleData]]
        ] = {}  # trading_pair -> interval -> candles
        self.last_candle_time: dict[
            str, dict[str, int]
        ] = {}  # trading_pair -> interval -> timestamp

        # WebSocket connections
        self.ws_connections: set[web.WebSocketResponse] = set()
        self.subscriptions: dict[
            str, set[web.WebSocketResponse]
        ] = {}  # subscription_key -> connected websockets

        # Trading pairs and their initial prices
        self.trading_pairs: dict[str, float] = {}

        # Network simulation
        self.latency_ms = 0  # Artificial latency
        self.packet_loss_rate = 0.0  # Packet loss rate 0.0-1.0
        self.error_rate = 0.0  # Error response rate 0.0-1.0

        # Rate limiting
        self.rate_limits: dict[str, dict[str, int]] = {
            "rest": {"limit": 1200, "period_ms": 60000},  # 1200 requests per minute
            "ws": {"limit": 5, "burst": 10},  # 5 messages per second with 10 burst
        }
        self.request_counts: dict[str, dict[str, deque]] = {
            "rest": {},
            "ws": {},  # ip -> timestamps
        }

        # Background tasks
        self._tasks: list[asyncio.Task] = []

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Set up the server routes based on the plugin configuration."""
        # Add REST routes
        for path, (method, handler_name) in self.plugin.rest_routes.items():
            handler = getattr(self, handler_name, None)
            if handler is None:
                # If the handler is not found as a method of this class,
                # check if it's a method of the plugin
                plugin_handler = getattr(self.plugin, handler_name, None)
                if plugin_handler:
                    # Create a wrapper that calls the plugin handler
                    async def wrapper(request, _handler=plugin_handler):
                        return await _handler(self, request)

                    handler = wrapper
                else:
                    self.logger.error(f"Handler {handler_name} not found for path {path}")
                    continue

            if method.upper() == "GET":
                self.app.router.add_get(path, handler)
            elif method.upper() == "POST":
                self.app.router.add_post(path, handler)
            elif method.upper() == "PUT":
                self.app.router.add_put(path, handler)
            elif method.upper() == "DELETE":
                self.app.router.add_delete(path, handler)

        # Add WebSocket routes
        for path, handler_name in self.plugin.ws_routes.items():
            handler = getattr(self, handler_name, None)
            if handler is None:
                # If the handler is not found as a method of this class,
                # check if it's a method of the plugin
                plugin_handler = getattr(self.plugin, handler_name, None)
                if plugin_handler:
                    # Create a wrapper that calls the plugin handler
                    async def wrapper(request, _handler=plugin_handler):
                        return await _handler(self, request)

                    handler = wrapper
                else:
                    self.logger.error(f"WebSocket handler {handler_name} not found for path {path}")
                    continue

            self.app.router.add_get(path, handler)

    def add_trading_pair(self, trading_pair: str, interval: str, initial_price: float = 50000.0):
        """
        Add a trading pair with initial candle data.

        Args:
            trading_pair: Trading pair symbol (e.g., "BTCUSDT")
            interval: Candle interval (e.g., "1m")
            initial_price: Initial price for candle generation
        """
        # Normalize the trading pair to the standard format
        trading_pair = self.plugin.normalize_trading_pair(trading_pair)

        # Initialize storage
        if trading_pair not in self.candles:
            self.candles[trading_pair] = {}
            self.last_candle_time[trading_pair] = {}
            self.trading_pairs[trading_pair] = initial_price

        # Initialize interval storage
        if interval not in self.candles[trading_pair]:
            self.candles[trading_pair][interval] = []

            # Generate historical candles
            end_time = int(time.time())
            interval_seconds = self._interval_to_seconds(interval)

            # Create 150 historical candles
            prev_candle = None
            for i in range(150):
                timestamp = end_time - (149 - i) * interval_seconds

                # Add some price trend over time
                price_factor = 1.0 + ((i - 75) / 300.0)  # From -0.25 to +0.25 change
                trend_price = initial_price * price_factor

                # Create candle
                candle = CandleDataFactory.create_random(
                    timestamp=timestamp,
                    previous_candle=prev_candle,
                    base_price=trend_price,
                    volatility=0.005,  # 0.5% volatility
                )

                self.candles[trading_pair][interval].append(candle)
                prev_candle = candle

            # Set last candle time
            self.last_candle_time[trading_pair][interval] = end_time

    def set_network_conditions(
        self,
        latency_ms: int | None = None,
        packet_loss_rate: float | None = None,
        error_rate: float | None = None,
    ):
        """
        Set network condition parameters for simulation.

        Args:
            latency_ms: Artificial latency in milliseconds
            packet_loss_rate: Rate of packet loss (0.0-1.0)
            error_rate: Rate of error responses (0.0-1.0)
        """
        if latency_ms is not None:
            self.latency_ms = max(0, latency_ms)

        if packet_loss_rate is not None:
            self.packet_loss_rate = max(0.0, min(1.0, packet_loss_rate))

        if error_rate is not None:
            self.error_rate = max(0.0, min(1.0, error_rate))

    def set_rate_limits(
        self,
        rest_limit: int | None = None,
        rest_period_ms: int | None = None,
        ws_limit: int | None = None,
        ws_burst: int | None = None,
    ):
        """
        Set rate limiting parameters.

        Args:
            rest_limit: Number of REST requests allowed per period
            rest_period_ms: Period for REST rate limit in milliseconds
            ws_limit: Number of WebSocket messages per second
            ws_burst: Maximum burst of WebSocket messages
        """
        if rest_limit is not None:
            self.rate_limits["rest"]["limit"] = max(1, rest_limit)

        if rest_period_ms is not None:
            self.rate_limits["rest"]["period_ms"] = max(1000, rest_period_ms)

        if ws_limit is not None:
            self.rate_limits["ws"]["limit"] = max(1, ws_limit)

        if ws_burst is not None:
            self.rate_limits["ws"]["burst"] = max(1, ws_burst)

    async def start(self):
        """Start the mock exchange server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        self.logger.info(
            f"Mock {self.exchange_type.value} server started at http://{self.host}:{self.port}"
        )

        # Start background tasks
        self._tasks.append(asyncio.create_task(self._generate_candles()))

        return f"http://{self.host}:{self.port}"

    async def stop(self):
        """Stop the mock exchange server."""
        # Cancel all background tasks
        for task in self._tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks = []

        # Close all WebSocket connections
        for ws in self.ws_connections:
            await ws.close()
        self.ws_connections.clear()
        self.subscriptions.clear()

        # Stop the server
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

        self.logger.info(f"Mock {self.exchange_type.value} server stopped")

    async def _generate_candles(self):
        """Generate new candles periodically for all trading pairs."""
        try:
            while True:
                current_time = int(time.time())

                for trading_pair in self.candles:
                    for interval in self.candles[trading_pair]:
                        interval_seconds = self._interval_to_seconds(interval)
                        last_time = self.last_candle_time[trading_pair][interval]

                        # Check if it's time to generate a new candle
                        if (
                            current_time >= last_time + interval_seconds
                            and self.candles[trading_pair][interval]
                        ):
                            last_candle = self.candles[trading_pair][interval][-1]

                            # Generate a new candle based on the last one
                            new_candle = CandleDataFactory.create_random(
                                timestamp=last_time + interval_seconds,
                                previous_candle=last_candle,
                                volatility=0.005,  # 0.5% volatility
                            )

                            # Add the new candle
                            self.candles[trading_pair][interval].append(new_candle)

                            # Update the last candle time
                            self.last_candle_time[trading_pair][interval] += interval_seconds

                            # Update trading pair price
                            self.trading_pairs[trading_pair] = new_candle.close

                            # Send WebSocket update to subscribers
                            await self._broadcast_candle_update(trading_pair, interval, new_candle)

                # Wait for a second
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            self.logger.info("Candle generation task cancelled")
            raise

    @staticmethod
    def _interval_to_seconds(interval: str) -> int:
        """Convert interval string to seconds."""
        unit = interval[-1]
        value = int(interval[:-1])

        if unit == "s":
            return value
        elif unit == "m":
            return value * 60
        elif unit == "h":
            return value * 60 * 60
        elif unit == "d":
            return value * 24 * 60 * 60
        elif unit == "w":
            return value * 7 * 24 * 60 * 60
        elif unit == "M":
            return value * 30 * 24 * 60 * 60
        else:
            raise ValueError(f"Unknown interval unit: {unit}")

    def _check_rate_limit(self, ip: str, api_type: str) -> bool:
        """
        Check if the client exceeds rate limits.

        Args:
            ip: Client IP address
            api_type: API type ('rest' or 'ws')

        Returns:
            True if allowed, False if rate limited
        """
        now = int(time.time() * 1000)

        # Initialize tracking for this IP if not exists
        if ip not in self.request_counts[api_type]:
            self.request_counts[api_type][ip] = deque()

        # Get rate limit parameters
        if api_type == "rest":
            limit = self.rate_limits["rest"]["limit"]
            period_ms = self.rate_limits["rest"]["period_ms"]

            # Clean up old timestamps
            while (
                self.request_counts[api_type][ip]
                and now - self.request_counts[api_type][ip][0] > period_ms
            ):
                self.request_counts[api_type][ip].popleft()

            # Check if limit exceeded
            if len(self.request_counts[api_type][ip]) >= limit:
                return False

        elif api_type == "ws":
            limit = self.rate_limits["ws"]["limit"]
            burst = self.rate_limits["ws"]["burst"]

            # For WebSocket, check 1-second rate
            while (
                self.request_counts[api_type][ip]
                and now - self.request_counts[api_type][ip][0] > 1000
            ):
                self.request_counts[api_type][ip].popleft()

            # Allow burst, but then enforce rate limit
            if len(self.request_counts[api_type][ip]) >= burst:
                # Once burst exceeded, enforce normal rate
                second_count = sum(
                    bool(now - ts <= 1000) for ts in self.request_counts[api_type][ip]
                )
                if second_count >= limit:
                    return False

        # Record this request
        self.request_counts[api_type][ip].append(now)
        return True

    async def _simulate_network_conditions(self):
        """Simulate network latency and potential packet loss."""
        # Simulate latency
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)

        # Simulate packet loss
        if self.packet_loss_rate > 0 and random.random() < self.packet_loss_rate:
            raise web.HTTPServiceUnavailable(reason="Simulated packet loss")

        # Simulate errors
        if self.error_rate > 0 and random.random() < self.error_rate:
            error_codes = [400, 403, 429, 500, 502, 503]
            error_code = random.choice(error_codes)

            if error_code == 429:
                raise web.HTTPTooManyRequests(reason="Rate limit exceeded")
            elif error_code == 400:
                raise web.HTTPBadRequest(reason="Invalid parameters")
            elif error_code == 403:
                raise web.HTTPForbidden(reason="Forbidden")
            elif error_code == 500:
                raise web.HTTPInternalServerError(reason="Internal server error")
            elif error_code == 502:
                raise web.HTTPBadGateway(reason="Bad gateway")
            elif error_code == 503:
                raise web.HTTPServiceUnavailable(reason="Service unavailable")

    async def _broadcast_candle_update(
        self, trading_pair: str, interval: str, candle: CandleData, is_final: bool = True
    ):
        """
        Broadcast a candle update to WebSocket subscribers.

        Args:
            trading_pair: The trading pair
            interval: The candle interval
            candle: The candle data to broadcast
            is_final: Whether this is the final candle update (closed candle)
        """
        # Get the subscription key for this trading pair and interval
        subscription_key = self.plugin.create_ws_subscription_key(trading_pair, interval)

        if subscription_key in self.subscriptions:
            # Format the message according to exchange type
            message = self.plugin.format_ws_candle_message(candle, trading_pair, interval, is_final)

            # Send to all subscribers
            for ws in self.subscriptions[subscription_key]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    self.logger.error(f"Error sending WebSocket message: {e}")

    # Common REST endpoint handlers

    async def handle_ping(self, request):
        """Handle ping endpoint."""
        await self._simulate_network_conditions()

        # Check rate limit
        client_ip = request.remote
        if not self._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        return web.json_response({})

    async def handle_time(self, request):
        """Handle time endpoint."""
        await self._simulate_network_conditions()

        # Check rate limit
        client_ip = request.remote
        if not self._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        return web.json_response({"serverTime": int(time.time() * 1000)})

    async def handle_klines(self, request):
        """
        Handle klines (candles) endpoint.

        This is a generic handler that uses the plugin to parse parameters
        and format the response.
        """
        await self._simulate_network_conditions()

        # Check rate limit
        client_ip = request.remote
        if not self._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        # Parse parameters using the plugin
        try:
            params = self.plugin.parse_rest_candles_params(request)
        except Exception as e:
            self.logger.error(f"Error parsing parameters: {e}")
            return web.json_response({"error": "Invalid parameters"}, status=400)

        symbol = params.get("symbol")
        interval = params.get("interval")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        limit = params.get("limit", 500)

        # Validate parameters
        if not symbol or not interval:
            return web.json_response({"error": "Missing required parameters"}, status=400)

        # Normalize the trading pair
        symbol = self.plugin.normalize_trading_pair(symbol)

        # Check if we have data for this trading pair and interval
        if symbol not in self.candles:
            # Add this trading pair with default data
            self.add_trading_pair(symbol, interval)

        if interval not in self.candles[symbol]:
            # Add this interval to the trading pair
            self.add_trading_pair(symbol, interval)

        # Parse time parameters
        try:
            start_time_sec = int(start_time) / 1000 if start_time else 0
            end_time_sec = int(end_time) / 1000 if end_time else int(time.time())
            limit_int = min(int(limit), 1000)  # Maximum 1000 candles
        except (ValueError, TypeError):
            start_time_sec = 0
            end_time_sec = int(time.time())
            limit_int = 500

        # Filter candles by time range
        filtered_candles = [
            candle
            for candle in self.candles[symbol][interval]
            if start_time_sec <= candle.timestamp <= end_time_sec
        ]

        # Apply limit
        limited_candles = filtered_candles[-limit_int:]

        # Format response based on exchange type
        response = self.plugin.format_rest_candles(limited_candles, symbol, interval)

        return web.json_response(response)

    # WebSocket endpoint handler

    async def handle_websocket(self, request):
        """
        Handle WebSocket connections.

        This is a generic handler that delegates to the plugin for
        exchange-specific message handling.
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.ws_connections.add(ws)

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_ws_message(ws, msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(
                        f"WebSocket connection closed with exception {ws.exception()}"
                    )
        finally:
            # Cleanup on disconnect
            self._remove_ws_connection(ws)

        return ws

    async def _handle_ws_message(self, ws: web.WebSocketResponse, message: str):
        """
        Handle incoming WebSocket message.

        This method delegates to the plugin for exchange-specific message parsing.
        """
        client_ip = "ws_client"  # Could track per client if needed

        # Check rate limit
        if not self._check_rate_limit(client_ip, "ws"):
            await ws.send_json({"error": "Rate limit exceeded"})
            return

        try:
            data = json.loads(message)

            # Use the plugin to parse the subscription message
            subscriptions = self.plugin.parse_ws_subscription(data)

            if subscriptions:
                # Add subscriptions
                for trading_pair, interval in subscriptions:
                    # Normalize the trading pair
                    trading_pair = self.plugin.normalize_trading_pair(trading_pair)

                    # Add trading pair if it doesn't exist
                    if (
                        trading_pair not in self.candles
                        or interval not in self.candles[trading_pair]
                    ):
                        self.add_trading_pair(trading_pair, interval)

                    # Create subscription key
                    subscription_key = self.plugin.create_ws_subscription_key(
                        trading_pair, interval
                    )

                    # Add subscription
                    if subscription_key not in self.subscriptions:
                        self.subscriptions[subscription_key] = set()
                    self.subscriptions[subscription_key].add(ws)

                # Send subscription success response
                success_response = self.plugin.create_ws_subscription_success(data, subscriptions)
                await ws.send_json(success_response)

            # Ping/pong handling
            elif "ping" in data or "op" == "ping" or "method" == "ping":
                # Generic ping response (exchange-specific ping handling should be in the plugin)
                await ws.send_json({"pong": int(time.time() * 1000)})

        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON message: {message}")
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")

    def _remove_ws_connection(self, ws: web.WebSocketResponse):
        """Remove WebSocket connection and subscriptions."""
        if ws in self.ws_connections:
            self.ws_connections.remove(ws)

        # Remove from subscriptions
        for channel, subscribers in list(self.subscriptions.items()):
            if ws in subscribers:
                subscribers.remove(ws)
                if not subscribers:
                    del self.subscriptions[channel]
