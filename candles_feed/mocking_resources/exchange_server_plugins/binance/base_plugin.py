import json
import random
import time
from abc import ABC
from typing import Any, Dict

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.binance.constants import SPOT_REST_URL, SPOT_WSS_URL
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class BinanceBasePlugin(ExchangePlugin, ABC):
    """
    Base class for Binance exchange plugins.

    This class provides shared functionality for Binance spot and perpetual plugins.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the Binance base plugin.

        :param exchange_type: The exchange type.
        """
        super().__init__(exchange_type, adapter_class)

    @property
    def rate_limits(self) -> Dict:
        """
        Get the rate limits for Binance.

        :returns: A dictionary containing REST and WebSocket rate limits.
        """
        return {
            "rest": {
                "limit": 1200,  # Base weight limit
                "period_ms": 60000,  # 1 minute window (Binance uses 1 minute)
                "weights": {  # Endpoint-specific weights
                    "/api/v3/ping": 1,
                    "/api/v3/time": 1,
                    "/api/v3/klines": 2,  # Candles have higher weight
                    "/api/v3/uiKlines": 2,
                    "/api/v3/exchangeInfo": 10,
                    "/api/v3/ticker/price": 2,
                    "/api/v3/ticker/24hr": 40,
                    "/api/v3/depth": 10,
                    "/api/v3/trades": 5,
                    "/api/v3/historicalTrades": 10,
                    "/api/v3/aggTrades": 5,
                    "/api/v3/account": 10,
                    "/api/v3/order": 2,
                    "/api/v3/openOrders": 3,
                    "/api/v3/allOrders": 10,
                    "/api/v3/myTrades": 10,
                    "/fapi/v1/klines": 2,
                    "/fapi/v1/time": 1,
                    "/fapi/v1/exchangeInfo": 10,
                }
            },
            "ws": {
                "limit": 5,  # Messages per second
                "burst": 10,  # Max burst
                "connection_limit": 50,  # Max concurrent connections
                "subscription_limit": 1000,  # Total subscriptions allowed
            }
        }

    @property
    def api_keys(self) -> Dict:
        """
        Get the test API keys for Binance.

        :returns: A dictionary of test API keys with associated metadata.
        """
        return {
            "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A": {
                "api_secret": "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j",
                "permissions": ["SPOT", "MARGIN", "FUTURES"],
                "ip_whitelist": ["*"],  # Allowed IPs, * means all
                "created_time": int(time.time() * 1000) - 86400000,  # 1 day ago
                "enabled": True
            },
            "TESTKEY123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ": {
                "api_secret": "TESTSECRET123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "permissions": ["SPOT"],
                "ip_whitelist": ["127.0.0.1"],
                "created_time": int(time.time() * 1000),
                "enabled": True
            }
        }

    @property
    def network_settings(self) -> Dict:
        """
        Get network settings for Binance.

        :returns: A dictionary of network-related settings.
        """
        return {
            "websocket_keep_alive": {
                "interval_seconds": 180,  # 3 minutes for Binance
                "type": "ping"  # Binance uses ping for keep-alive
            }
        }

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Binance.

        :returns: The base REST API URL.
        """
        return f"{SPOT_REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Binance.

        :returns: The base WebSocket API URL.
        """
        return f"{SPOT_WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Binance.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    async def handle_websocket(self, server, request):
        """
        Handle WebSocket connections for Binance.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: WebSocket response.
        """
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
                        data = json.loads(msg.data)
                        method = data.get("method")

                        if method == "SUBSCRIBE":
                            # Parse subscriptions using our plugin method
                            subscriptions = self.parse_ws_subscription(data)

                            # Create subscription keys and add to server's subscriptions
                            for trading_pair, interval in subscriptions:
                                # Normalize trading pair
                                for pair in server.candles:
                                    if self.normalize_trading_pair(pair).replace("-", "") == trading_pair.replace("-", ""):
                                        trading_pair = pair
                                        break

                                # Create subscription key
                                subscription_key = self.create_ws_subscription_key(trading_pair, interval)

                                # Add to subscriptions
                                if subscription_key not in server.subscriptions:
                                    server.subscriptions[subscription_key] = set()

                                server.subscriptions[subscription_key].add(ws)

                                # Send the current candle immediately if available
                                if trading_pair in server.candles and interval in server.candles[trading_pair]:
                                    candles = server.candles[trading_pair][interval]
                                    if candles:
                                        current_candle = candles[-1]
                                        message = self.format_ws_candle_message(
                                            candle=current_candle,
                                            trading_pair=trading_pair,
                                            interval=interval,
                                            is_final=True
                                        )
                                        await ws.send_json(message)

                            # Send subscription success response
                            success_response = self.create_ws_subscription_success(data, subscriptions)
                            await ws.send_json(success_response)

                        elif method == "UNSUBSCRIBE":
                            # Parse subscriptions
                            subscriptions = self.parse_ws_subscription(data)

                            # Remove from subscriptions
                            for trading_pair, interval in subscriptions:
                                # Find the actual trading pair
                                for pair in server.candles:
                                    if self.normalize_trading_pair(pair).replace("-", "") == trading_pair.replace("-", ""):
                                        trading_pair = pair
                                        break

                                # Create subscription key
                                subscription_key = self.create_ws_subscription_key(trading_pair, interval)

                                # Remove from subscriptions
                                if subscription_key in server.subscriptions:
                                    server.subscriptions[subscription_key].discard(ws)

                                    # Remove the set if empty
                                    if not server.subscriptions[subscription_key]:
                                        del server.subscriptions[subscription_key]

                            # Send unsubscription success response
                            success_response = self.create_ws_subscription_success(data, subscriptions)
                            await ws.send_json(success_response)

                        else:
                            # Unknown method
                            await ws.send_json({
                                "error": f"Unknown method: {method}",
                                "id": data.get("id")
                            })

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
            # Clean up when connection is closed
            server.ws_connections.discard(ws)

            # Remove from all subscriptions
            for sub_set in server.subscriptions.values():
                sub_set.discard(ws)

            # Clean up empty subscription sets
            empty_keys = [k for k, v in server.subscriptions.items() if not v]
            for k in empty_keys:
                del server.subscriptions[k]

        return ws

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str, timezone_adjustment_ms: int = 0
    ) -> list:
        """
        Format candle data as a Binance REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param timezone_adjustment_ms: Optional timezone adjustment in milliseconds.
        :returns: Formatted response as expected from Binance's REST API.
        """
        # Binance returns an array of candles directly, not wrapped in an object
        # Format according to Binance API:
        # [
        #   [
        #     1499040000000,      // Open time
        #     "0.01634790",       // Open
        #     "0.80000000",       // High
        #     "0.01575800",       // Low
        #     "0.01577100",       // Close
        #     "148976.11427815",  // Volume
        #     1499644799999,      // Close time
        #     "2434.19055334",    // Quote asset volume
        #     308,                // Number of trades
        #     "1756.87402397",    // Taker buy base asset volume
        #     "28.46694368",      // Taker buy quote asset volume
        #     "17928899.62484339" // Ignore
        #   ]
        # ]

        interval_ms = self._interval_to_milliseconds(interval)

        return [
            [
                # Apply timezone adjustment if provided
                int(c.timestamp_ms) + timezone_adjustment_ms,  # Open time
                str(c.open),                                   # Open
                str(c.high),                                   # High
                str(c.low),                                    # Low
                str(c.close),                                  # Close
                str(c.volume),                                 # Volume
                int(c.timestamp_ms) + interval_ms + timezone_adjustment_ms,  # Close time
                str(c.quote_asset_volume),                     # Quote asset volume
                100,                                           # Number of trades (placeholder)
                str(c.volume * 0.7),                           # Taker buy base asset volume (placeholder)
                str(c.quote_asset_volume * 0.7),               # Taker buy quote asset volume (placeholder)
                "0"                                            # Ignore
            ]
            for c in candles
        ]

    def _interval_to_milliseconds(self, interval: str) -> int:
        """
        Convert interval string to milliseconds.

        :param interval: Interval string (e.g., "1m", "1h", "1d")
        :returns: Interval in milliseconds
        """
        unit = interval[-1]
        value = int(interval[:-1])

        if unit == "m":
            return value * 60 * 1000
        elif unit == "h":
            return value * 60 * 60 * 1000
        elif unit == "d":
            return value * 24 * 60 * 60 * 1000
        elif unit == "w":
            return value * 7 * 24 * 60 * 60 * 1000
        else:
            return 60 * 1000  # Default to 1m


    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a Binance WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from Binance's WebSocket API.
        """
        # Format according to Binance WebSocket API:
        # {
        #   "e": "kline",     // Event type
        #   "E": 1672515782136,  // Event time
        #   "s": "BNBBTC",    // Symbol
        #   "k": {
        #     "t": 1672515780000, // Kline start time
        #     "T": 1672515839999, // Kline close time
        #     "s": "BNBBTC",   // Symbol
        #     "i": "1m",      // Interval
        #     "f": 100,       // First trade ID
        #     "L": 200,       // Last trade ID
        #     "o": "0.0010",  // Open price
        #     "c": "0.0020",  // Close price
        #     "h": "0.0025",  // High price
        #     "l": "0.0015",  // Low price
        #     "v": "1000",    // Base asset volume
        #     "n": 100,       // Number of trades
        #     "x": false,     // Is this kline closed?
        #     "q": "1.0000",  // Quote asset volume
        #     "V": "500",     // Taker buy base asset volume
        #     "Q": "0.500",   // Taker buy quote asset volume
        #     "B": "123456"   // Ignore
        #   }
        # }

        symbol = trading_pair.replace("-", "")
        close_time = int(candle.timestamp_ms) + self._interval_to_milliseconds(interval)

        return {
            "e": "kline",
            "E": int(candle.timestamp_ms),
            "s": symbol,
            "k": {
                "t": int(candle.timestamp_ms),
                "T": close_time,
                "s": symbol,
                "i": interval,
                "f": 0,
                "L": 100,
                "o": str(candle.open),
                "c": str(candle.close),
                "h": str(candle.high),
                "l": str(candle.low),
                "v": str(candle.volume),
                "n": 100,
                "x": is_final,
                "q": str(candle.quote_asset_volume),
                "V": str(candle.volume * 0.7),
                "Q": str(candle.quote_asset_volume * 0.7),
                "B": "0"
            }
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Binance WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions = []

        # Binance uses a different subscription format:
        # {
        #   "method": "SUBSCRIBE",
        #   "params": [
        #     "btcusdt@kline_1m",
        #     "ethusdt@kline_5m"
        #   ],
        #   "id": 1
        # }

        if message.get("method") == "SUBSCRIBE":
            for param in message.get("params", []):
                # Format is: "btcusdt@kline_1m"
                if "@kline_" in param:
                    parts = param.split("@kline_")
                    if len(parts) == 2:
                        symbol = parts[0].upper()
                        interval = parts[1]

                        # Convert symbol to standardized format (e.g., BTC-USDT)
                        for i in range(len(symbol) - 1, 2, -1):
                            if symbol[i:] in ["USDT", "BTC", "ETH", "USD", "USDC"]:
                                symbol = f"{symbol[:i]}-{symbol[i:]}"
                                break

                        subscriptions.append((symbol, interval))

        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a Binance WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        # Binance returns a success response with the subscription ID:
        # {
        #   "result": null,
        #   "id": 1
        # }
        return {
            "result": None,
            "id": message.get("id", 1)
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        # Format according to Binance subscription format: "btcusdt@kline_1m"
        symbol = trading_pair.replace("-", "").lower()
        return f"{symbol}@kline_{interval}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for Binance candle requests.

        Extended to support all Binance klines parameters:
        - symbol: Trading pair (required)
        - interval: Candle interval (1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
        - startTime: Start time in milliseconds
        - endTime: End time in milliseconds
        - timeZone: Time zone adjustment (-12:00 to +14:00)
        - limit: Number of candles to return (default 500, max 1000)

        :param request: The web request.
        :returns: A dictionary with standardized parameter names or error information
        """
        params = request.query
        result = {
            "valid": True,
            "error": None
        }

        # Get all Binance klines parameters
        symbol = params.get("symbol")
        interval = params.get("interval")
        start_time = params.get("startTime")
        end_time = params.get("endTime")
        time_zone = params.get("timeZone", "0")
        limit = params.get("limit")

        # Validate required parameters
        if not symbol:
            result["valid"] = False
            result["error"] = {
                "code": -1102,
                "msg": "Mandatory parameter 'symbol' not sent or invalid."
            }
            return result

        # Validate interval
        valid_intervals = ["1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
        if not interval:
            result["valid"] = False
            result["error"] = {
                "code": -1120,
                "msg": "Mandatory parameter 'interval' not sent or invalid."
            }
            return result
        elif interval not in valid_intervals:
            result["valid"] = False
            result["error"] = {
                "code": -1121,
                "msg": f"Invalid interval: {interval}. Supported intervals: {', '.join(valid_intervals)}"
            }
            return result

        # Validate time parameters
        if start_time and end_time:
            try:
                start_time_int = int(start_time)
                end_time_int = int(end_time)
                if end_time_int <= start_time_int:
                    result["valid"] = False
                    result["error"] = {
                        "code": -1125,
                        "msg": "Invalid parameter: endTime must be greater than startTime"
                    }
                    return result
            except ValueError:
                result["valid"] = False
                result["error"] = {
                    "code": -1104,
                    "msg": "Not a valid timeframe format"
                }
                return result

        # Process limit parameter
        if limit is not None:
            try:
                limit = int(limit)
                if limit <= 0:
                    result["valid"] = False
                    result["error"] = {
                        "code": -1127,
                        "msg": "Limit must be greater than 0"
                    }
                    return result
                if limit > 1000:  # Binance limit is 1000
                    limit = 1000
            except ValueError:
                result["valid"] = False
                result["error"] = {
                    "code": -1128,
                    "msg": "Limit must be an integer"
                }
                return result
        else:
            limit = 500  # Default limit

        # Parse timezone offset if provided
        timezone_offset_hours = 0
        try:
            if ":" in time_zone:
                hours, minutes = time_zone.split(":")
                timezone_offset_hours = int(hours) + (int(minutes) / 60)
            else:
                timezone_offset_hours = int(time_zone)

            # Validate timezone ranges
            if timezone_offset_hours < -12 or timezone_offset_hours > 14:
                result["valid"] = False
                result["error"] = {
                    "code": -1130,
                    "msg": "Invalid timeZone parameter: must be between -12:00 and +14:00"
                }
                return result
        except (ValueError, TypeError):
            result["valid"] = False
            result["error"] = {
                "code": -1130,
                "msg": "Invalid timeZone parameter format"
            }
            return result

        # Map Binance parameters to generic parameters expected by handle_klines
        result.update({
            "symbol": symbol,            # 'symbol' is the same in both
            "interval": interval,        # 'interval' is the same in both
            "start_time": start_time,    # 'startTime' in Binance maps to 'start_time' in generic handler
            "end_time": end_time,        # 'endTime' in Binance maps to 'end_time' in generic handler
            "time_zone": time_zone,      # 'timeZone' in Binance maps to 'time_zone'
            "limit": limit,              # 'limit' has the same name

            # Also keep the original Binance parameter names for reference
            "startTime": start_time,
            "endTime": end_time,
            "timeZone": time_zone,
            "timezone_offset_hours": timezone_offset_hours,
        })

        return result

    async def handle_depth(self, server, request):
        """
        Handle the Binance order book depth endpoint.

        Endpoint: /api/v3/depth

        Parameters:
        - symbol: Trading pair
        - limit: Number of price levels to return (default 100, max 5000)

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with order book data.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Parse parameters
        params = request.query
        symbol = params.get("symbol")
        limit_str = params.get("limit", "100")

        # Validate parameters
        if not symbol:
            return web.json_response(
                {"code": -1102, "msg": "Mandatory parameter 'symbol' not sent or invalid."},
                status=400
            )

        try:
            limit = int(limit_str)
            if limit <= 0:
                return web.json_response(
                    {"code": -1100, "msg": "Illegal parameter format: limit"},
                    status=400
                )
            if limit > 5000:
                limit = 5000
        except ValueError:
            return web.json_response(
                {"code": -1100, "msg": "Illegal parameter format: limit"},
                status=400
            )

        # Generate mock order book data
        timestamp = int(time.time() * 1000)

        # Find the trading pair price
        trading_pair = symbol.upper()
        normalized_pair = ""
        for pair in server.trading_pairs:
            if pair.replace("-", "") == trading_pair:
                normalized_pair = pair
                break

        if not normalized_pair:
            # Trading pair not found, return empty response
            return web.json_response(
                {"code": -1121, "msg": f"Invalid symbol: {symbol}"},
                status=400
            )

        # Get the last candle to determine current price
        current_price = 50000.0  # Default price
        for interval in server.candles.get(normalized_pair, {}):
            candles = server.candles[normalized_pair][interval]
            if candles:
                current_price = candles[-1].close
                break

        # Generate bids and asks around the current price
        bids = []
        asks = []

        # Create decreasing bids below current price
        for i in range(limit):
            price = current_price * (1 - 0.0001 * (i + 1))
            quantity = random.uniform(0.1, 10.0)
            bids.append([f"{price:.8f}", f"{quantity:.8f}"])

        # Create increasing asks above current price
        for i in range(limit):
            price = current_price * (1 + 0.0001 * (i + 1))
            quantity = random.uniform(0.1, 10.0)
            asks.append([f"{price:.8f}", f"{quantity:.8f}"])

        # Format response according to Binance API
        response = {
            "lastUpdateId": timestamp,
            "bids": bids,
            "asks": asks
        }

        return web.json_response(response)

    async def handle_ticker_price(self, server, request):
        """
        Handle the Binance price ticker endpoint.

        Endpoint: /api/v3/ticker/price

        Parameters:
        - symbol: Trading pair (optional)

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with price ticker data.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Parse parameters
        params = request.query
        symbol = params.get("symbol")

        # If symbol is provided, return data for just that symbol
        if symbol:
            trading_pair = symbol.upper()
            normalized_pair = ""
            for pair in server.trading_pairs:
                if pair.replace("-", "") == trading_pair:
                    normalized_pair = pair
                    break

            if not normalized_pair:
                # Trading pair not found, return error
                return web.json_response(
                    {"code": -1121, "msg": f"Invalid symbol: {symbol}"},
                    status=400
                )

            # Get the last candle to determine current price
            current_price = 50000.0  # Default price
            for interval in server.candles.get(normalized_pair, {}):
                candles = server.candles[normalized_pair][interval]
                if candles:
                    current_price = candles[-1].close
                    break

            response = {
                "symbol": trading_pair,
                "price": f"{current_price:.8f}"
            }

            return web.json_response(response)

        # If no symbol is provided, return data for all symbols
        else:
            prices = []

            for pair in server.trading_pairs:
                trading_pair = pair.replace("-", "")

                # Get the last candle to determine current price
                current_price = 50000.0  # Default price
                for interval in server.candles.get(pair, {}):
                    candles = server.candles[pair][interval]
                    if candles:
                        current_price = candles[-1].close
                        break

                prices.append({
                    "symbol": trading_pair,
                    "price": f"{current_price:.8f}"
                })

            return web.json_response(prices)

    async def handle_account(self, server, request):
        """
        Handle the Binance account endpoint.

        Endpoint: /api/v3/account

        Authentication required:
        - X-MBX-APIKEY header
        - Signature parameters

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with account information.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Verify authentication (this is an authenticated endpoint)
        auth_result = server.verify_authentication(request, required_permissions=["SPOT"])
        if not auth_result["authenticated"]:
            return web.json_response(auth_result["error"], status=401)

        # Generate mock account data
        balances = []

        # Add some common assets
        for asset in ["BTC", "ETH", "USDT", "BNB", "SOL", "DOGE"]:
            free = random.uniform(0.1, 100.0)
            locked = random.uniform(0.0, 10.0)

            balances.append({
                "asset": asset,
                "free": f"{free:.8f}",
                "locked": f"{locked:.8f}"
            })

        # Add balances for all trading pairs in the server
        for pair in server.trading_pairs:
            base, quote = pair.split("-")

            # Check if the asset is already in the balances
            if not any(b["asset"] == base for b in balances):
                free = random.uniform(0.1, 100.0)
                locked = random.uniform(0.0, 10.0)

                balances.append({
                    "asset": base,
                    "free": f"{free:.8f}",
                    "locked": f"{locked:.8f}"
                })

        response = {
            "makerCommission": 10,
            "takerCommission": 10,
            "buyerCommission": 0,
            "sellerCommission": 0,
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": True,
            "updateTime": int(time.time() * 1000),
            "accountType": "SPOT",
            "balances": balances,
            "permissions": ["SPOT"]
        }

        return web.json_response(response)

    async def handle_instruments(self, server, request):
        """
        Handle the Binance instruments endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with exchange information.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        inst_type_query = request.query.get("instType")
        if not inst_type_query:
            return web.json_response({"error": "instType is required"}, status=400)

        instruments = []
        for trading_pair in server.trading_pairs:
            base, quote = trading_pair.split("-", 1)
            instruments.append(
                {
                    "instType": inst_type_query,
                    "instId": trading_pair.replace("-", "/"),
                    "uly": trading_pair,
                    "baseCcy": base,
                    "quoteCcy": quote,
                    "settleCcy": quote,
                    "ctValCcy": quote,
                    "optType": "C", # or "P" for put options
                    "stk": trading_pair,
                    "listTime": int(server._time() * 1000),
                    "expTime": int(server._time() * 1000) + 3600 * 24 * 30 * 1000, # 30 days from now
                    "lever": "10",
                    "tickSz": "0.01",
                    "lotSz": "1",
                    "minSz": "1",
                    "ctVal": "1",
                    "state": "live",
                }
            )

        response = {"code": "0", "msg": "", "data": instruments}
        return web.json_response(response)


    @staticmethod
    def _interval_to_seconds(interval: str) -> int:
        """Convert interval string to seconds.

        :param interval: The interval string.
        :returns: The interval in seconds.
        :raises ValueError: If the interval unit is unknown.
        """
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
        else:
            raise ValueError(f"Unknown interval unit: {unit}")

    async def handle_ping(self, server, request):
        """
        Handle Binance ping request (health check).

        :param server: The mock server instance.
        :param request: The web request.
        :returns: Empty JSON response.
        """
        await server._simulate_network_conditions()

        # Check rate limits
        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Return empty response (Binance ping response format)
        return web.json_response({})

    async def handle_time(self, server, request):
        """
        Handle Binance server time request.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: JSON response with server time.
        """
        await server._simulate_network_conditions()

        # Check rate limits
        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Return current server time
        return web.json_response({"serverTime": int(server._time() * 1000)})

    async def handle_exchange_info(self, server, request):
        """
        Handle Binance exchange information request.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: JSON response with exchange information.
        """
        await server._simulate_network_conditions()

        # Check rate limits
        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Build response with trading pair information
        symbols = []
        for trading_pair in server.candles:
            # Extract base and quote from trading pair (e.g., "BTC-USDT" -> "BTC", "USDT")
            if "-" in trading_pair:
                base, quote = trading_pair.split("-")
            else:
                # Default parsing for non-standard formats
                if len(trading_pair) <= 6:  # Short pairs like BTCETH
                    base, quote = trading_pair[:3], trading_pair[3:]
                else:  # Longer pairs like BTCUSDT
                    base, quote = trading_pair[:-4], trading_pair[-4:]

            # Add symbol information
            symbols.append({
                "symbol": trading_pair.replace("-", ""),
                "status": "TRADING",
                "baseAsset": base,
                "baseAssetPrecision": 8,
                "quoteAsset": quote,
                "quotePrecision": 8,
                "orderTypes": ["LIMIT", "MARKET"],
                "icebergAllowed": True,
                "filters": [
                    {
                        "filterType": "PRICE_FILTER",
                        "minPrice": "0.00000001",
                        "maxPrice": "100000.00000000",
                        "tickSize": "0.00000001"
                    },
                    {
                        "filterType": "LOT_SIZE",
                        "minQty": "0.00100000",
                        "maxQty": "100000.00000000",
                        "stepSize": "0.00100000"
                    }
                ]
            })

        # Prepare response
        response = {
            "timezone": "UTC",
            "serverTime": int(server._time() * 1000),
            "rateLimits": [
                {
                    "rateLimitType": "REQUEST_WEIGHT",
                    "interval": "MINUTE",
                    "intervalNum": 1,
                    "limit": server.rate_limits.get("rest", {}).get("limit", 1200)
                }
            ],
            "exchangeFilters": [],
            "symbols": symbols
        }

        return web.json_response(response)

    async def handle_klines(self, server, request):
        """
        Handle candle data request for Binance.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: JSON response with candle data.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": -1003, "msg": "Too many requests"}, status=429)

        # Parse parameters using our plugin method - handle both async and sync methods
        import inspect
        if inspect.iscoroutinefunction(self.parse_rest_candles_params):
            params = await self.parse_rest_candles_params(request)
        else:
            params = self.parse_rest_candles_params(request)

        # Check if parameters are valid
        if not params.get("valid", True):
            return web.json_response(params.get("error", {"msg": "Invalid parameters"}), status=400)

        symbol = params.get("symbol")
        interval = params.get("interval")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        limit = params.get("limit", 500)
        timezone_offset_hours = params.get("timezone_offset_hours", 0)

        # Find the trading pair in our list (may need normalization)
        trading_pair = None
        for pair in server.candles:
            if self.normalize_trading_pair(pair).replace("-", "") == symbol:
                trading_pair = pair
                break

        if not trading_pair:
            return web.json_response(
                {"code": -1121, "msg": f"Invalid symbol: {symbol}"}, status=400
            )

        # Check if we have this interval
        if interval not in server.candles.get(trading_pair, {}):
            return web.json_response(
                {"code": -1120, "msg": f"Invalid interval: {interval}"}, status=400
            )

        # Get the candles
        candles = server.candles[trading_pair][interval]

        # Filter by time if specified
        if start_time:
            start_time = int(start_time)
            # Convert to ms if in seconds
            if start_time < 10000000000:
                start_time *= 1000
            candles = [c for c in candles if c.timestamp_ms >= start_time]

        if end_time:
            end_time = int(end_time)
            # Convert to ms if in seconds
            if end_time < 10000000000:
                end_time *= 1000
            candles = [c for c in candles if c.timestamp_ms <= end_time]

        # Apply limit
        if limit and len(candles) > limit:
            candles = candles[-limit:]

        # Format response using our method
        timezone_adjustment_ms = int(timezone_offset_hours * 3600 * 1000)
        response_data = self.format_rest_candles(
            candles, trading_pair, interval, timezone_adjustment_ms
        )

        return web.json_response(response_data)

