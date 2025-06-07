"""
A simple mock server plugin for the MockedExchangeServer.

This plugin implements a basic, standardized exchange API for testing purposes.
It doesn't emulate any specific exchange but provides a consistent interface
that can be used for unit testing the mock server framework.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple  # Added Dict, List, Tuple, Optional

from aiohttp import web  # type: ignore

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.adapter import MockedAdapter
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class MockedPlugin(ExchangePlugin):
    """
    A simple mock plugin implementation for testing the mock server framework.

    This plugin provides a standardized set of REST and WebSocket endpoints
    with consistent, predictable formatting, making it suitable for testing
    the mock server without depending on exchange-specific implementations.
    """

    def __init__(self, exchange_type: ExchangeType = ExchangeType.MOCK):
        """
        Initialize the simple mock plugin.

        :param exchange_type: The exchange type, defaults to ExchangeType.MOCK
        """
        # Initialize with None as adapter_class since we're just mocking for tests
        super().__init__(exchange_type, MockedAdapter)  # type: ignore

        # Initialize trading pairs dictionary to store pair configurations
        self.trading_pairs: Dict[str, Dict[str, float]] = {}

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL.

        :returns: The base REST API URL.
        """
        return "https://mock-exchange.test/api"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL.

        :returns: The base WebSocket API URL.
        """
        return "wss://mock-exchange.test/ws"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/candles": ("GET", "handle_klines"),
            "/api/v3/klines": ("GET", "handle_klines"),
            "/api/time": ("GET", "handle_time"),
            "/api/v3/time": ("GET", "handle_time"),
            "/api/v3/ping": ("GET", "handle_ping"),
            "/api/instruments": ("GET", "handle_instruments"),
        }

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as a REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response dictionary.
        """
        # Format candles as dictionaries
        interval_ms: int = self._interval_to_milliseconds(interval)

        formatted_candles: List[Dict[str, Any]] = [
            {
                "timestamp": int(candle.timestamp_ms),  # type: ignore
                "open": str(candle.open),  # type: ignore
                "high": str(candle.high),  # type: ignore
                "low": str(candle.low),  # type: ignore
                "close": str(candle.close),  # type: ignore
                "volume": str(candle.volume),  # type: ignore
                "close_time": int(candle.timestamp_ms) + interval_ms,  # type: ignore
                "quote_volume": str(candle.quote_asset_volume)  # type: ignore
                if candle.quote_asset_volume  # type: ignore
                else "0",
                "trades": 100,
                "taker_base_volume": str(candle.volume * 0.7),  # type: ignore
                "taker_quote_volume": str(candle.quote_asset_volume * 0.7)  # type: ignore
                if candle.quote_asset_volume  # type: ignore
                else "0",
            }
            for candle in candles
        ]

        # Return a structured response with metadata
        return {
            "status": "ok",
            "symbol": trading_pair,
            "interval": interval,
            "data": formatted_candles,
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message.
        """
        # Return a standardized WebSocket message format
        return {  # type: ignore
            "type": "candle_update",  # type: ignore
            "symbol": trading_pair,  # type: ignore
            "interval": interval,  # type: ignore
            "is_final": is_final,  # type: ignore
            "data": {  # type: ignore
                "timestamp": int(candle.timestamp_ms),  # type: ignore
                "open": str(candle.open),  # type: ignore
                "high": str(candle.high),  # type: ignore
                "low": str(candle.low),  # type: ignore
                "close": str(candle.close),  # type: ignore
                "volume": str(candle.volume),  # type: ignore
                "quote_volume": str(candle.quote_asset_volume)  # type: ignore
                if candle.quote_asset_volume  # type: ignore
                else "0",
            },
        }

    def parse_ws_subscription(self, message: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        Parse a WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions: List[Tuple[str, str]] = []

        # Support both our format and the Binance format for compatibility
        if message.get("type") == "subscribe":
            # Our format
            for sub in message.get("subscriptions", []):
                trading_pair = sub.get("symbol")
                interval = sub.get("interval")
                if trading_pair and interval:
                    subscriptions.append((trading_pair, interval))
        elif message.get("method") == "SUBSCRIBE":
            # Binance format
            for param in message.get("params", []):
                # Format is: "btcusdt@kline_1m"
                if "@kline_" in param:
                    parts = param.split("@kline_")
                    if len(parts) == 2:
                        symbol = parts[0].upper()
                        interval = parts[1]
                        subscriptions.append((symbol, interval))

        return subscriptions

    def create_ws_subscription_success(
        self, message: Dict[str, Any], subscriptions: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """
        Create a WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        # Handle the Binance format if it's detected
        if message.get("method") == "SUBSCRIBE":
            # Binance format response
            return {"result": None, "id": message.get("id", 1)}

        # Otherwise, use our standard format
        subscription_details = [
            {"symbol": pair, "interval": interval} for pair, interval in subscriptions
        ]

        return {
            "type": "subscribe_result",
            "status": "success",
            "subscriptions": subscription_details,
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        return f"{trading_pair}_{interval}"

    def add_trading_pair(self, trading_pair: str, interval: str, base_price: float) -> None:
        """
        Add a trading pair with a specific interval and base price for testing.

        This method is used in tests to configure the mock plugin with specific
        trading pairs and their associated data.

        :param trading_pair: The trading pair to add (e.g., "BTC-USDT").
        :param interval: The candle interval (e.g., "1m", "5m", "1h").
        :param base_price: The base price to use for generating mock candles.
        """
        if trading_pair not in self.trading_pairs:
            self.trading_pairs[trading_pair] = {}

        self.trading_pairs[trading_pair][interval] = base_price

    def get_base_price(self, trading_pair: str) -> float:
        """
        Get the base price for a trading pair.

        :param trading_pair: The trading pair.
        :returns: The base price, or 100.0 if not found.
        """
        return next(
            (
                next(iter(intervals.values()))
                for pair, intervals in self.trading_pairs.items()
                if pair == trading_pair and intervals
            ),
            100.0,
        )

    def get_interval_seconds(self, interval: str) -> int:
        """
        Get the number of seconds in an interval.

        :param interval: The interval string (e.g., "1m", "1h").
        :returns: The number of seconds.
        """
        return self._interval_to_seconds(interval)

    def normalize_trading_pair(self, trading_pair: str) -> str:
        """
        Normalize a trading pair to a standardized format.

        :param trading_pair: The trading pair to normalize.
        :returns: The normalized trading pair.
        """
        # If already contains a separator, return as is
        if "-" in trading_pair:
            return trading_pair

        # Try to find common quote asset patterns
        for quote in ["USDT", "USD", "BTC", "ETH", "BNB", "USDC"]:
            if trading_pair.endswith(quote):
                base = trading_pair[: -len(quote)]
                return f"{base}-{quote}"

        # Default case: assume last 4 characters are the quote asset
        if len(trading_pair) > 4:
            base = trading_pair[:-4]
            quote = trading_pair[-4:]
            return f"{base}-{quote}"

        # If all else fails, return as is
        return trading_pair

    def _interval_to_seconds(self, interval: str) -> int:
        """
        Convert interval string to seconds.

        :param interval: The interval string (e.g., "1m", "1h", "1d").
        :returns: The interval in seconds.
        """
        unit: str = interval[-1]
        try:
            value: int = int(interval[:-1])
        except ValueError:
            # If conversion fails, default to 1 minute
            return 60

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
        else:
            return 60  # Default to 1 minute

    def _interval_to_milliseconds(self, interval: str) -> int:
        """
        Convert interval string to milliseconds.

        :param interval: The interval string (e.g., "1m", "1h", "1d").
        :returns: The interval in milliseconds.
        """
        # Convert seconds to milliseconds
        return self._interval_to_seconds(interval) * 1000

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query

        # Extract standard parameters
        symbol = params.get("symbol")
        interval = params.get("interval")
        limit = params.get("limit")
        start_time = params.get("start_time")
        end_time = params.get("end_time")

        # Convert limit to int if provided
        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                limit = 1000  # Default value

        # Return standardized parameter dict
        return {  # type: ignore
            "symbol": symbol,  # type: ignore
            "interval": interval,  # type: ignore
            "limit": limit,  # type: ignore
            "start_time": start_time,  # type: ignore
            "end_time": end_time,  # type: ignore
        }

    async def handle_time(self, server, request: web.Request) -> web.Response:
        """
        Handle the time endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with server time.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        current_time_ms: int = int(server._time() * 1000)

        return web.json_response(
            {"status": "ok", "timestamp": current_time_ms, "server_time": current_time_ms}
        )

    async def handle_instruments(self, server, request: web.Request) -> web.Response:
        """
        Handle the instruments endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with available instruments.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        instruments: List[Dict[str, str]] = []
        for trading_pair_str in server.trading_pairs:
            base, quote = (
                trading_pair_str.split("-")
                if "-" in trading_pair_str  # Corrected variable
                else (trading_pair_str[:-4], trading_pair_str[-4:])  # Corrected variable
            )
            instruments.append(
                {
                    "symbol": trading_pair_str,  # Corrected variable
                    "base_asset": base,
                    "quote_asset": quote,
                    "status": "TRADING",
                }
            )

        return web.json_response({"status": "ok", "instruments": instruments})

    async def handle_ping(self, server, request: web.Request) -> web.Response:
        """
        Handle ping endpoint (health check).

        :param server: The mock server instance.
        :param request: The web request.
        :returns: Empty JSON response.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        # Return empty response
        return web.json_response({})

    async def handle_websocket(self, server, request: web.Request) -> web.WebSocketResponse:
        """
        Handle WebSocket connections.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: WebSocket response.
        """
        # Apply artificial latency to initial connection
        if server.latency_ms > 0:
            await asyncio.sleep(server.latency_ms / 1000.0)

        # Check connection limit
        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "ws"):
            return web.Response(status=429, text="Too many requests")

        # Create WebSocket
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Add to active connections
        server.ws_connections.add(ws)

        # Handle WebSocket messages
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data_dict: Dict[str, Any] = json.loads(msg.data)
                        if (
                            data_dict.get("type") == "subscribe"
                            or data_dict.get("method") == "SUBSCRIBE"
                        ):
                            # Parse subscriptions
                            subscriptions_list: List[Tuple[str, str]] = self.parse_ws_subscription(
                                data_dict
                            )

                            # Handle method (either our format with type="subscribe" or Binance format with method="SUBSCRIBE")
                            method_str: str = (
                                "SUBSCRIBE"
                                if data_dict.get("method") == "SUBSCRIBE"
                                else "subscribe"
                            )

                            # Create success response first (before sending data)
                            success_response_dict: Dict[str, Any]
                            if method_str == "subscribe":
                                # Our format
                                success_response_dict = {
                                    "type": "subscribe_result",
                                    "status": "success",
                                    "subscriptions": [
                                        {"symbol": pair_str, "interval": interval_str_val}
                                        for pair_str, interval_str_val in subscriptions_list
                                    ],
                                }
                            else:
                                # Binance format
                                success_response_dict = {
                                    "result": None,
                                    "id": data_dict.get("id", 1),
                                }

                            # Send response immediately
                            await ws.send_json(success_response_dict)

                            # Handle subscriptions
                            for trading_pair_str, interval_str in subscriptions_list:
                                # Find the actual trading pair in server
                                normalized_pair_str: Optional[str] = None
                                for pair_key_str in server.candles:
                                    if (
                                        self.normalize_trading_pair(pair_key_str)
                                        .replace("-", "")
                                        .lower()
                                        == trading_pair_str.lower()
                                        or pair_key_str.lower() == trading_pair_str.lower()
                                    ):
                                        normalized_pair_str = pair_key_str
                                        break

                                if normalized_pair_str and interval_str in server.candles.get(
                                    normalized_pair_str, {}
                                ):
                                    # Create subscription key
                                    subscription_key_str: str = self.create_ws_subscription_key(
                                        normalized_pair_str, interval_str
                                    )

                                    # Add to subscriptions
                                    if subscription_key_str not in server.subscriptions:
                                        server.subscriptions[subscription_key_str] = set()

                                    server.subscriptions[subscription_key_str].add(ws)

                                    # Send the current candle (optional after confirmation)
                                    candles_list: List[CandleData] = server.candles[
                                        normalized_pair_str
                                    ][interval_str]
                                    if candles_list:
                                        current_candle_obj: CandleData = candles_list[-1]
                                        message_dict: Dict[str, Any] = (
                                            self.format_ws_candle_message(
                                                candle=current_candle_obj,
                                                trading_pair=normalized_pair_str,
                                                interval=interval_str,
                                                is_final=True,
                                            )
                                        )
                                        # Delay sending initial data to ensure subscription confirmation is processed first
                                        await asyncio.sleep(0.1)
                                        await ws.send_json(message_dict)

                        elif data_dict.get("method") == "UNSUBSCRIBE":
                            # Parse subscriptions
                            subscriptions_list = self.parse_ws_subscription(data_dict)

                            # Unsubscribe from each topic
                            for trading_pair_str, interval_str in subscriptions_list:
                                current_pair_str = trading_pair_str  # Keep original for key creation if not found normalized
                                for pair_key_str in server.candles:
                                    if (
                                        self.normalize_trading_pair(pair_key_str)
                                        .replace("-", "")
                                        .lower()
                                        == trading_pair_str.lower()
                                    ):
                                        current_pair_str = pair_key_str
                                        break

                                # Create subscription key
                                subscription_key_str = self.create_ws_subscription_key(
                                    current_pair_str, interval_str
                                )

                                # Remove from subscriptions
                                if subscription_key_str in server.subscriptions:
                                    server.subscriptions[subscription_key_str].discard(ws)

                                    # Remove the set if empty
                                    if not server.subscriptions[subscription_key_str]:
                                        del server.subscriptions[subscription_key_str]

                            # Send unsubscription success response
                            unsub_success_response: Dict[str, Any] = (
                                self.create_ws_subscription_success(data_dict, subscriptions_list)
                            )
                            await ws.send_json(unsub_success_response)

                    except json.JSONDecodeError:
                        await ws.send_json({"error": "Invalid JSON"})
                    except Exception as e:
                        await ws.send_json({"error": f"Error: {str(e)}"})

                elif msg.type == web.WSMsgType.ERROR:
                    server.logger.error(
                        f"WebSocket connection closed with exception: {ws.exception()}"
                    )
                    break

        finally:
            # Clean up when the connection is closed
            server.ws_connections.discard(ws)

            # Remove from all subscriptions
            for subscribers in server.subscriptions.values():
                subscribers.discard(ws)

            # Clean up empty subscription lists
            empty_keys = [k for k, v in server.subscriptions.items() if not v]
            for k in empty_keys:
                del server.subscriptions[k]

        return ws

    async def handle_klines(self, server, request: web.Request) -> web.Response:
        """
        Handle the klines (candles) endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: JSON response with candle data.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        # Parse parameters
        params_dict: Dict[str, Any] = self.parse_rest_candles_params(request)
        symbol_str: Optional[str] = params_dict.get("symbol")
        interval_str: Optional[str] = params_dict.get("interval")
        limit_val: Optional[int] = params_dict.get(
            "limit"
        )  # Already int or None from parse_rest_candles_params

        limit_int: int = (
            limit_val if limit_val is not None else 1000
        )  # Default if not provided or invalid

        # Find the trading pair in our list
        trading_pair_found: Optional[str] = None
        if symbol_str:
            for pair_key_str in server.candles:
                if pair_key_str.replace("-", "") == symbol_str:
                    trading_pair_found = pair_key_str
                    break
            if not trading_pair_found:
                # Try to find by normalized symbol
                for pair_key_str in server.candles:
                    if (
                        pair_key_str.lower() == symbol_str.lower()
                        or pair_key_str.replace("-", "").lower() == symbol_str.lower()
                    ):
                        trading_pair_found = pair_key_str
                        break

        if not trading_pair_found:
            return web.json_response({"error": f"Symbol not found: {symbol_str}"}, status=404)

        # Check if we have this interval
        if not interval_str or interval_str not in server.candles.get(trading_pair_found, {}):
            return web.json_response({"error": f"Interval not found: {interval_str}"}, status=404)

        # Get the candles
        candles_list: List[CandleData] = server.candles[trading_pair_found][interval_str]

        # Apply limit
        if limit_int and len(candles_list) > limit_int:
            candles_list = candles_list[-limit_int:]

        # Format candles
        formatted_candles_dict: Dict[str, Any] = self.format_rest_candles(
            candles_list, trading_pair_found, interval_str
        )

        # Return the response
        return web.json_response(formatted_candles_dict)
