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

from .candle_data_factory import CandleDataFactory
from .exchange_plugin import ExchangePlugin

if TYPE_CHECKING:
    from .exchange_type import ExchangeType


class MockedExchangeServer:
    """
    Configurable mock server for cryptocurrency exchange API simulation.

    This server provides REST and WebSocket endpoints that simulate
    the behavior of various exchanges for testing purposes.
    """

    def __init__(self, plugin: ExchangePlugin, host: str = "127.0.0.1", port: int = 8080):
        """
        Initialize the mock exchange server.

        :param plugin: The exchange plugin to use for exchange-specific behavior.
        :param host: Host to bind the server to.
        :param port: Port to bind the server to.
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

        # Get exchange-specific settings from the plugin
        # Rate limiting
        self.rate_limits = plugin.rate_limits.copy()

        # Default IP limits if not provided by the plugin
        if "ip_limits" not in self.rate_limits.get("rest", {}):
            self.rate_limits.setdefault("rest", {})["ip_limits"] = {
                "default": self.rate_limits.get("rest", {}).get("limit", 1200),
                "strict": self.rate_limits.get("rest", {}).get("limit", 1200) // 2,
            }

        self.request_counts: dict[str, dict[str, deque | dict]] = {
            "rest": {
                # Format: {ip: {"timestamps": deque(), "weights": deque()}}
            },
            "ws": {
                # Format: {ip: {"timestamps": deque(), "subscriptions": set()}}
            },
        }

        # Authentication simulation with exchange-specific settings
        # Get API keys from the plugin
        exchange_name = self.exchange_type.value.split("_")[
            0
        ]  # Extract exchange name (e.g., "binance" from "binance_spot")

        # Initialize the API keys structure
        self.api_keys = {exchange_name: plugin.api_keys}

        # Exchange-specific settings from the plugin's network_settings
        self.exchange_settings = plugin.network_settings

        # Background tasks
        self._tasks: list[asyncio.Task] = []

        # Setup routes
        self._setup_routes()
        self._url: str = ""

    @property
    def mocked_exchange_url(self) -> str:
        """
        Get the URL of the mock exchange server.

        :returns: The URL of the mock exchange server.
        """
        if not self._url:
            raise RuntimeError("Server not started")
        return self._url

    def add_trading_pair(self, trading_pair: str, interval: str, initial_price: float = 50000.0):
        """
        Add a trading pair to the mock server with initial candles.

        :param trading_pair: The trading pair (e.g., "BTC-USDT").
        :param interval: The candle interval (e.g., "1m").
        :param initial_price: The initial price for the trading pair.
        """
        self.trading_pairs[trading_pair] = initial_price

        if trading_pair not in self.candles:
            self.candles[trading_pair] = {}
            self.last_candle_time[trading_pair] = {}

        if interval not in self.candles[trading_pair]:
            self.candles[trading_pair][interval] = []
            self.last_candle_time[trading_pair][interval] = 0

        # Generate some initial candles
        self._generate_initial_candles(trading_pair, interval, initial_price)
        self.logger.info(f"Added trading pair {trading_pair} with interval {interval}")

    def _generate_initial_candles(
        self, trading_pair: str, interval: str, initial_price: float, num_candles: int = 200
    ):
        """
        Generate initial candles for a trading pair and interval.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param initial_price: The initial price.
        :param num_candles: The number of candles to generate (reduced to 200 to speed up tests).
        """
        factory = CandleDataFactory()

        # Get interval in seconds
        interval_seconds = self.plugin._interval_to_seconds(interval)

        # Use current time as base and go backward
        end_timestamp = int(self._time())
        start_timestamp = end_timestamp - (interval_seconds * num_candles)

        # For testing, create simpler candles with minimal price deviation (1%)
        if num_candles > 20:
            # Create simple trending series with very small volatility to stay close to initial price
            candles = factory.create_trending_series(
                start_timestamp=start_timestamp,
                count=num_candles,
                interval_seconds=interval_seconds,
                start_price=initial_price,
                trend=0.0001,  # Almost flat trend
                volatility=0.001,  # Very low volatility
                max_deviation=0.01,  # Maximum 1% deviation
            )
        else:
            # Create candles using the market simulation method (with constraints)
            candles = factory.create_market_simulation(
                start_timestamp=start_timestamp,
                count=num_candles,
                interval_seconds=interval_seconds,
                initial_price=initial_price,
            )

        self.candles[trading_pair][interval] = candles
        if candles:
            # Convert timestamp to milliseconds if needed
            timestamp = candles[-1].timestamp
            self.last_candle_time[trading_pair][interval] = (
                int(timestamp * 1000) if timestamp < 10000000000 else timestamp
            )

    def _setup_routes(self):
        """Set up the routes for the server."""
        # Add REST routes from the plugin
        for route_path, (method, handler_name) in self.plugin.rest_routes.items():
            if hasattr(self.plugin, handler_name):
                handler = getattr(self.plugin, handler_name)
                if handler:
                    if method == "GET":
                        self.app.router.add_get(route_path, self._wrap_rest_handler(handler))
                    elif method == "POST":
                        self.app.router.add_post(route_path, self._wrap_rest_handler(handler))
                    elif method == "PUT":
                        self.app.router.add_put(route_path, self._wrap_rest_handler(handler))
                    elif method == "DELETE":
                        self.app.router.add_delete(route_path, self._wrap_rest_handler(handler))
                    else:
                        self.logger.warning(f"Unsupported method: {method} for {route_path}")
                else:
                    self.logger.warning(f"Handler {handler_name} not found in plugin")
            else:
                self.logger.warning(f"Handler {handler_name} not found in plugin")

        # Add WebSocket routes from the plugin
        for ws_path, handler_name in self.plugin.ws_routes.items():
            if hasattr(self.plugin, handler_name):
                handler = getattr(self.plugin, handler_name)
                if handler:
                    self.app.router.add_get(ws_path, self._wrap_ws_handler(handler))
                else:
                    self.logger.warning(f"WebSocket handler {handler_name} not found in plugin")
            else:
                self.logger.warning(f"WebSocket handler {handler_name} not found in plugin")

    def _wrap_rest_handler(self, handler):
        """
        Wrap a REST handler to handle network conditions and rate limiting.

        :param handler: The handler to wrap.
        :returns: The wrapped handler.
        """

        async def wrapped_handler(request):
            try:
                # Check for artificial network conditions
                if self.packet_loss_rate > 0 and random.random() < self.packet_loss_rate:
                    # Simulate packet loss by not responding
                    return web.Response(status=408, text="Request timed out")

                if self.error_rate > 0 and random.random() < self.error_rate:
                    # Simulate a server error
                    error_responses = [
                        {"code": 500, "msg": "Internal server error"},
                        {"code": 502, "msg": "Bad gateway"},
                        {"code": 503, "msg": "Service unavailable"},
                        {"code": 504, "msg": "Gateway timeout"},
                    ]
                    error = random.choice(error_responses)
                    return web.json_response(error, status=error["code"])

                # Apply artificial latency
                if self.latency_ms > 0:
                    await asyncio.sleep(self.latency_ms / 1000.0)

                # Handle the request with the real handler
                return await handler(self, request)
            except Exception as e:
                self.logger.exception(f"Error in REST handler: {e}")
                return web.json_response(
                    {"code": -1000, "msg": f"An unknown error occurred: {str(e)}"},
                    status=500,
                )

        return wrapped_handler

    def _wrap_ws_handler(self, handler):
        """
        Wrap a WebSocket handler to handle network conditions.

        :param handler: The handler to wrap.
        :returns: The wrapped handler.
        """

        async def wrapped_handler(request):
            try:
                # Apply artificial latency to initial connection
                if self.latency_ms > 0:
                    await asyncio.sleep(self.latency_ms / 1000.0)

                # Handle the WebSocket connection with the real handler
                return await handler(self, request)
            except Exception as e:
                self.logger.exception(f"Error in WebSocket handler: {e}")
                return web.Response(status=500, text=f"WebSocket error: {str(e)}")

        return wrapped_handler

    async def start(self) -> str:
        """
        Start the mock exchange server.

        :returns: The URL of the server.
        """
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        self._url = f"http://{self.host}:{self.port}"
        self.logger.info(f"Mock exchange server started at {self._url}")

        # Start background tasks
        self._start_background_tasks()

        return self._url

    def _start_background_tasks(self):
        """Start background tasks for the server."""
        # Start a task to generate candles
        task = asyncio.create_task(self._generate_candles_periodically())
        self._tasks.append(task)

        # Add more background tasks as needed

    async def stop(self):
        """Stop the mock exchange server."""
        # Cancel all background tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        self._tasks.clear()

        # Close all WebSocket connections
        for ws in list(self.ws_connections):
            if not ws.closed:
                await ws.close(code=1001, message="Server shutting down")

        self.ws_connections.clear()
        self.subscriptions.clear()

        # Stop the server
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

        self.logger.info("Mock exchange server stopped")

    async def _generate_candles_periodically(self):
        """
        Generate candles periodically for all trading pairs and intervals.

        This runs as a background task to keep updating candles.
        """
        try:
            while True:
                current_time = self._time()
                int(current_time * 1000)

                for trading_pair, intervals in self.candles.items():
                    for interval in intervals:
                        factory = CandleDataFactory()

                        # Get the previous candle as a base for generating the next one
                        last_candles = self.candles[trading_pair][interval]
                        if not last_candles:
                            continue

                        last_candle = last_candles[-1]

                        # Make sure timestamp is in seconds for calculation
                        last_time = last_candle.timestamp
                        if last_time > 10000000000:  # If in milliseconds, convert to seconds
                            last_time = last_time / 1000

                        # Calculate interval in seconds
                        interval_seconds = self.plugin._interval_to_seconds(interval)

                        # Generate candles to catch up to current time
                        while last_time + interval_seconds <= current_time:
                            next_time = last_time + interval_seconds

                            # Get initial price for this trading pair
                            initial_price = self.trading_pairs.get(trading_pair, 50000.0)

                            # Generate a new candle based on the last one using create_random
                            # but constrained to stay close to initial price
                            new_candle = factory.create_random(
                                timestamp=int(next_time),
                                previous_candle=last_candle,
                                volatility=0.001,  # Reduced volatility (0.1%)
                                max_deviation=0.01,  # Maximum 1% deviation from initial
                                initial_price=initial_price,
                            )

                            # Add to the list
                            last_candles.append(new_candle)

                            # Keep only the last 1000 candles
                            if len(last_candles) > 1000:
                                last_candles.pop(0)

                            # Update last time and candle
                            last_time = next_time
                            last_candle = new_candle

                            # Update the last candle time (in ms for consistency)
                            self.last_candle_time[trading_pair][interval] = int(last_time * 1000)

                            # Push candle update to WebSocket subscribers
                            await self._push_candle_update(
                                trading_pair, interval, new_candle, is_final=True
                            )

                # Sleep for a second before checking again
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.info("Candle generation task cancelled")
            raise

    async def _push_candle_update(
        self, trading_pair: str, interval: str, candle: CandleData, is_final: bool = False
    ):
        """
        Push a candle update to WebSocket subscribers.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param candle: The candle data.
        :param is_final: Whether this is the final update for this candle.
        """
        subscription_key = self.plugin.create_ws_subscription_key(trading_pair, interval)
        subscribers = self.subscriptions.get(subscription_key, set())

        if not subscribers:
            return

        # Format the message according to the exchange
        message = self.plugin.format_ws_candle_message(
            candle=candle, trading_pair=trading_pair, interval=interval, is_final=is_final
        )

        # Send to all subscribers
        for ws in list(subscribers):
            if not ws.closed:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    self.logger.error(f"Error sending WebSocket message: {e}")
                    # Remove the connection if there's an error
                    subscribers.discard(ws)
                    self.ws_connections.discard(ws)
            else:
                # Remove closed connections
                subscribers.discard(ws)
                self.ws_connections.discard(ws)

    def _time(self) -> float:
        """
        Get the current time.

        This is a wrapper around time.time() to allow for testing.

        :returns: The current time in seconds.
        """
        return time.time()

    def set_network_conditions(
        self, latency_ms: int = 0, packet_loss_rate: float = 0.0, error_rate: float = 0.0
    ):
        """
        Set network conditions for the mock server.

        :param latency_ms: Artificial latency in milliseconds.
        :param packet_loss_rate: Rate of packet loss (0.0-1.0).
        :param error_rate: Rate of error responses (0.0-1.0).
        """
        self.latency_ms = latency_ms
        self.packet_loss_rate = min(max(packet_loss_rate, 0.0), 1.0)
        self.error_rate = min(max(error_rate, 0.0), 1.0)
        self.logger.info(
            f"Network conditions set: latency={latency_ms}ms, "
            f"packet_loss={packet_loss_rate * 100:.1f}%, "
            f"error_rate={error_rate * 100:.1f}%"
        )

    async def _simulate_network_conditions(self):
        """Simulate network conditions for a request."""
        # Simulate packet loss
        if self.packet_loss_rate > 0 and random.random() < self.packet_loss_rate:
            raise web.HTTPRequestTimeout(text="Request timed out")

        # Simulate errors
        if self.error_rate > 0 and random.random() < self.error_rate:
            error_codes = [500, 502, 503, 504]
            error_code = random.choice(error_codes)
            if error_code == 500:
                raise web.HTTPInternalServerError(text=f"Error {error_code}")
            elif error_code == 502:
                raise web.HTTPBadGateway(text=f"Error {error_code}")
            elif error_code == 503:
                raise web.HTTPServiceUnavailable(text=f"Error {error_code}")
            elif error_code == 504:
                raise web.HTTPGatewayTimeout(text=f"Error {error_code}")

        # Simulate latency
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)

    def _check_rate_limit(self, ip: str, limit_type: str = "rest") -> bool:
        """
        Check if a request from an IP is within rate limits.

        :param ip: The IP address.
        :param limit_type: The type of limit to check ("rest" or "ws").
        :returns: True if within limits, False otherwise.
        """
        current_time = self._time() * 1000

        if limit_type == "rest":
            # Initialize tracking for this IP if not exists
            if ip not in self.request_counts["rest"]:
                self.request_counts["rest"][ip] = {"timestamps": deque(), "weights": deque()}

            # Get timestamps and weights for this IP
            timestamps = self.request_counts["rest"][ip]["timestamps"]
            weights = self.request_counts["rest"][ip]["weights"]

            # Remove expired entries (older than the rate limit period)
            period_ms = self.rate_limits["rest"]["period_ms"]
            while timestamps and current_time - timestamps[0] > period_ms:
                timestamps.popleft()
                weights.popleft()

            # Calculate total weight in the current period
            total_weight = sum(weights)

            # Check if adding this request would exceed the limit
            limit = self.rate_limits["rest"]["limit"]
            if total_weight >= limit:
                self.logger.warning(f"Rate limit exceeded for IP {ip}: {total_weight}/{limit}")
                return False

            # Add this request to the tracking
            timestamps.append(current_time)

            # Calculate weight for this request
            request_weight = 1  # Default weight
            # TODO: Determine request path and get specific weight

            weights.append(request_weight)
            return True

        elif limit_type == "ws":
            # Initialize tracking for this IP if not exists
            if ip not in self.request_counts["ws"]:
                self.request_counts["ws"][ip] = {"timestamps": deque(), "subscriptions": set()}

            # Get timestamps for this IP
            timestamps = self.request_counts["ws"][ip]["timestamps"]

            # Remove expired entries (older than 1 second for messages per second)
            while timestamps and current_time - timestamps[0] > 1000:
                timestamps.popleft()

            # Check if adding this message would exceed the limit
            limit = self.rate_limits["ws"]["limit"]
            if len(timestamps) >= limit:
                self.logger.warning(
                    f"WebSocket rate limit exceeded for IP {ip}: {len(timestamps)}/{limit}"
                )
                return False

            # Add this message to the tracking
            timestamps.append(current_time)
            return True

        return True

    def verify_authentication(self, request: web.Request, required_permissions=None) -> dict:
        """
        Verify authentication for a request.

        :param request: The web request.
        :param required_permissions: List of required permissions.
        :returns: Dict with authentication result and error if any.
        """
        # Check for API key in header
        api_key = request.headers.get("X-MBX-APIKEY")
        if not api_key:
            return {
                "authenticated": False,
                "error": {"code": -2015, "msg": "Invalid API-key, IP, or permissions."},
            }

        # Get exchange name
        exchange_name = self.exchange_type.value.split("_")[0]

        # Check if API key exists
        if exchange_name not in self.api_keys or api_key not in self.api_keys[exchange_name]:
            return {
                "authenticated": False,
                "error": {"code": -2015, "msg": "Invalid API-key, IP, or permissions."},
            }

        api_key_data = self.api_keys[exchange_name][api_key]

        # Check if API key is enabled
        if not api_key_data.get("enabled", True):
            return {
                "authenticated": False,
                "error": {"code": -2015, "msg": "Invalid API-key, IP, or permissions."},
            }

        # Check IP whitelist
        ip = request.remote
        ip_whitelist = api_key_data.get("ip_whitelist", ["*"])
        if "*" not in ip_whitelist and ip not in ip_whitelist:
            return {
                "authenticated": False,
                "error": {"code": -2015, "msg": "Invalid API-key, IP, or permissions."},
            }

        # Check permissions
        if required_permissions:
            permissions = api_key_data.get("permissions", [])
            if not all(perm in permissions for perm in required_permissions):
                return {
                    "authenticated": False,
                    "error": {"code": -2015, "msg": "Invalid API-key, IP, or permissions."},
                }

        # Authentication successful
        return {"authenticated": True, "error": None}

    async def handle_klines(self, request: web.Request):
        """
        Handle candle data request.

        :param request: The web request.
        :returns: JSON response with candle data.
        """
        await self._simulate_network_conditions()

        client_ip = request.remote
        if not self._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Parse parameters using the plugin's method
        params = self.plugin.parse_rest_candles_params(request)

        # Check if parameters are valid
        if not params.get("valid", True):
            return web.json_response(params.get("error", {"msg": "Invalid parameters"}), status=400)

        symbol = params.get("symbol")
        interval = params.get("interval")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        limit = params.get("limit", 500)

        # Find the trading pair in our list (may need normalization)
        trading_pair = None
        for pair in self.candles:
            if self.plugin.normalize_trading_pair(pair).replace("-", "") == symbol:
                trading_pair = pair
                break

        if not trading_pair:
            return web.json_response(
                {"code": -1121, "msg": f"Invalid symbol: {symbol}"}, status=400
            )

        # Check if we have this interval
        if interval not in self.candles.get(trading_pair, {}):
            return web.json_response(
                {"code": -1120, "msg": f"Invalid interval: {interval}"}, status=400
            )

        # Get the candles
        candles = self.candles[trading_pair][interval]

        # Filter by time if specified
        if start_time:
            start_time = int(start_time)
            candles = [c for c in candles if c.timestamp_ms >= start_time]

        if end_time:
            end_time = int(end_time)
            candles = [c for c in candles if c.timestamp_ms <= end_time]

        # Apply limit
        if limit and len(candles) > limit:
            candles = candles[-limit:]

        # Format response using the plugin's method
        # Check if timezone adjustment is needed
        timezone_offset_hours = params.get("timezone_offset_hours", 0)
        timezone_adjustment_ms = int(timezone_offset_hours * 3600 * 1000)

        response_data = self.plugin.format_rest_candles(
            candles, trading_pair, interval, timezone_adjustment_ms
        )

        return web.json_response(response_data)

    async def handle_time(self, request: web.Request):
        """
        Handle server time request.

        :param request: The web request.
        :returns: JSON response with server time.
        """
        await self._simulate_network_conditions()

        client_ip = request.remote
        if not self._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Return the current server time in milliseconds
        server_time = int(self._time() * 1000)
        return web.json_response({"serverTime": server_time})

    async def handle_ping(self, request: web.Request):
        """
        Handle ping request.

        :param request: The web request.
        :returns: Empty JSON response.
        """
        await self._simulate_network_conditions()

        client_ip = request.remote
        if not self._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Simple ping response (empty object for Binance)
        return web.json_response({})

    async def handle_exchange_info(self, request: web.Request):
        """
        Handle exchange information request.

        :param request: The web request.
        :returns: JSON response with exchange information.
        """
        await self._simulate_network_conditions()

        client_ip = request.remote
        if not self._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Basic exchange info (this can be customized by the plugin for each exchange)
        current_time = int(self._time() * 1000)

        # Create symbols info based on our trading pairs
        symbols = []
        exchange_filters = []

        for trading_pair in self.trading_pairs:
            # Split the trading pair (e.g., "BTC-USDT" -> "BTC", "USDT")
            if "-" in trading_pair:
                base, quote = trading_pair.split("-")
            else:
                # Handle pairs without separator (e.g., "BTCUSDT")
                # This is a simple heuristic - might need improvement for real use
                for i in range(len(trading_pair) - 1, 0, -1):
                    if trading_pair[i:] in ["USDT", "USD", "BTC", "ETH", "BNB"]:
                        base = trading_pair[:i]
                        quote = trading_pair[i:]
                        break
                else:
                    # Default fallback
                    base = trading_pair[:3]
                    quote = trading_pair[3:]

            # Format according to Binance API (customize for other exchanges)
            symbol_info = {
                "symbol": trading_pair.replace("-", ""),
                "status": "TRADING",
                "baseAsset": base,
                "baseAssetPrecision": 8,
                "quoteAsset": quote,
                "quotePrecision": 8,
                "quoteAssetPrecision": 8,
                "orderTypes": [
                    "LIMIT",
                    "LIMIT_MAKER",
                    "MARKET",
                    "STOP_LOSS",
                    "STOP_LOSS_LIMIT",
                    "TAKE_PROFIT",
                    "TAKE_PROFIT_LIMIT",
                ],
                "icebergAllowed": True,
                "ocoAllowed": True,
                "isSpotTradingAllowed": True,
                "isMarginTradingAllowed": False,
                "filters": [
                    {
                        "filterType": "PRICE_FILTER",
                        "minPrice": "0.00000100",
                        "maxPrice": "100000.00000000",
                        "tickSize": "0.00000100",
                    },
                    {
                        "filterType": "LOT_SIZE",
                        "minQty": "0.00100000",
                        "maxQty": "100000.00000000",
                        "stepSize": "0.00100000",
                    },
                    {"filterType": "MIN_NOTIONAL", "minNotional": "0.00100000"},
                ],
                "permissions": ["SPOT"],
            }
            symbols.append(symbol_info)

        # Common exchange filters
        exchange_filters = [
            {"filterType": "EXCHANGE_MAX_NUM_ORDERS", "maxNumOrders": 1000},
            {"filterType": "EXCHANGE_MAX_NUM_ALGO_ORDERS", "maxNumAlgoOrders": 200},
        ]

        # Build the response
        response = {
            "timezone": "UTC",
            "serverTime": current_time,
            "rateLimits": [
                {
                    "rateLimitType": "REQUEST_WEIGHT",
                    "interval": "MINUTE",
                    "intervalNum": 1,
                    "limit": self.rate_limits["rest"]["limit"],
                },
                {"rateLimitType": "ORDERS", "interval": "SECOND", "intervalNum": 10, "limit": 50},
                {"rateLimitType": "ORDERS", "interval": "DAY", "intervalNum": 1, "limit": 160000},
            ],
            "exchangeFilters": exchange_filters,
            "symbols": symbols,
        }

        return web.json_response(response)

    async def handle_websocket(self, request: web.Request):
        """
        Handle WebSocket connection.

        :param request: The web request.
        :returns: WebSocket response.
        """
        # Apply artificial latency to initial connection
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)

        # Check connection limit
        client_ip = request.remote
        if not self._check_rate_limit(client_ip, "ws"):
            return web.Response(status=429, text="Too many requests")

        # Create WebSocket
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Add to active connections
        self.ws_connections.add(ws)

        # Track this IP's connection count
        if client_ip not in self.request_counts["ws"]:
            self.request_counts["ws"][client_ip] = {"timestamps": deque(), "subscriptions": set()}

        # Handle WebSocket messages
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    if not self._check_rate_limit(client_ip, "ws"):
                        await ws.send_json({"error": "Rate limit exceeded"})
                        continue

                    try:
                        data = json.loads(msg.data)
                        method = data.get("method")

                        if method == "SUBSCRIBE":
                            await self._handle_subscription(ws, data, client_ip)
                        elif method == "UNSUBSCRIBE":
                            await self._handle_unsubscription(ws, data)
                        elif method == "LIST_SUBSCRIPTIONS":
                            # List current subscriptions
                            subs = self._get_subscriptions_for_connection(ws)
                            await ws.send_json({"result": subs, "id": data.get("id")})
                        else:
                            # Unknown method
                            await ws.send_json(
                                {"error": f"Unknown method: {method}", "id": data.get("id")}
                            )

                    except json.JSONDecodeError:
                        await ws.send_json({"error": "Invalid JSON"})
                    except Exception as e:
                        self.logger.error(f"Error handling WebSocket message: {e}")
                        await ws.send_json({"error": f"Error: {str(e)}"})

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(
                        f"WebSocket connection closed with exception: {ws.exception()}"
                    )
                    break

        finally:
            # Clean up when the connection is closed
            self._cleanup_websocket(ws)

        return ws

    async def _handle_subscription(self, ws: web.WebSocketResponse, data: dict, client_ip: str):
        """
        Handle WebSocket subscription.

        :param ws: The WebSocket connection.
        :param data: The subscription data.
        :param client_ip: The client IP address.
        """
        # Parse the subscription request using the plugin
        subscriptions = self.plugin.parse_ws_subscription(data)

        # Check subscription limit
        current_subs = self.request_counts["ws"][client_ip]["subscriptions"]
        if len(current_subs) + len(subscriptions) > self.rate_limits["ws"]["subscription_limit"]:
            await ws.send_json({"error": "Subscription limit exceeded", "id": data.get("id")})
            return

        # Subscribe to each topic
        for trading_pair, interval in subscriptions:
            # Normalize trading pair for our internal tracking
            for pair in self.candles:
                if self.plugin.normalize_trading_pair(pair).replace(
                    "-", ""
                ) == trading_pair.replace("-", ""):
                    trading_pair = pair
                    break

            # Create subscription key
            subscription_key = self.plugin.create_ws_subscription_key(trading_pair, interval)

            # Add to subscriptions
            if subscription_key not in self.subscriptions:
                self.subscriptions[subscription_key] = set()

            self.subscriptions[subscription_key].add(ws)

            # Track this client's subscriptions
            current_subs.add(subscription_key)

            # Send the current candle immediately
            candles = self.candles.get(trading_pair, {}).get(interval, [])
            if candles:
                current_candle = candles[-1]
                message = self.plugin.format_ws_candle_message(
                    candle=current_candle,
                    trading_pair=trading_pair,
                    interval=interval,
                    is_final=True,
                )
                await ws.send_json(message)

        # Send subscription success response
        success_response = self.plugin.create_ws_subscription_success(data, subscriptions)
        await ws.send_json(success_response)

    async def _handle_unsubscription(self, ws: web.WebSocketResponse, data: dict):
        """
        Handle WebSocket unsubscription.

        :param ws: The WebSocket connection.
        :param data: The unsubscription data.
        """
        # Parse the unsubscription request using the plugin
        subscriptions = self.plugin.parse_ws_subscription(data)

        # Unsubscribe from each topic
        for trading_pair, interval in subscriptions:
            # Normalize trading pair for our internal tracking
            for pair in self.candles:
                if self.plugin.normalize_trading_pair(pair).replace(
                    "-", ""
                ) == trading_pair.replace("-", ""):
                    trading_pair = pair
                    break

            # Create subscription key
            subscription_key = self.plugin.create_ws_subscription_key(trading_pair, interval)

            # Remove from subscriptions
            if subscription_key in self.subscriptions:
                self.subscriptions[subscription_key].discard(ws)

                # Remove the set if empty
                if not self.subscriptions[subscription_key]:
                    del self.subscriptions[subscription_key]

            # Remove from client's tracked subscriptions
            client_ip = ws.request.remote
            if client_ip in self.request_counts["ws"]:
                self.request_counts["ws"][client_ip]["subscriptions"].discard(subscription_key)

        # Send unsubscription success response (usually same format as subscription)
        success_response = self.plugin.create_ws_subscription_success(data, subscriptions)
        await ws.send_json(success_response)

    def _get_subscriptions_for_connection(self, ws: web.WebSocketResponse) -> list:
        """
        Get all subscriptions for a WebSocket connection.

        :param ws: The WebSocket connection.
        :returns: List of subscription keys.
        """
        result = []
        for sub_key, subscribers in self.subscriptions.items():
            if ws in subscribers:
                result.append(sub_key)
        return result

    def _cleanup_websocket(self, ws: web.WebSocketResponse):
        """
        Clean up a closed WebSocket connection.

        :param ws: The WebSocket connection.
        """
        # Remove from active connections
        self.ws_connections.discard(ws)

        # Remove from all subscriptions
        for subscribers in self.subscriptions.values():
            subscribers.discard(ws)

        # Clean up empty subscription lists
        empty_keys = [key for key, subscribers in self.subscriptions.items() if not subscribers]
        for key in empty_keys:
            del self.subscriptions[key]

        # Remove from client tracking
        if hasattr(ws, "request"):
            client_ip = ws.request.remote
            if client_ip in self.request_counts["ws"]:
                self.request_counts["ws"][client_ip]["subscriptions"] = set()
