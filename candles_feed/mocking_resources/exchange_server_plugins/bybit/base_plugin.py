"""
Base class for Bybit exchange plugins.

This class provides shared functionality for Bybit spot and perpetual plugins.
"""

from abc import ABC
from typing import Any

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.bybit.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class BybitBasePlugin(ExchangePlugin, ABC):
    """
    Base class for Bybit exchange plugins.

    This class provides shared functionality for Bybit spot and perpetual plugins.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the Bybit base plugin.

        :param exchange_type: The exchange type.
        :param adapter_class: The adapter class for this exchange.
        """
        super().__init__(exchange_type, adapter_class)

    @staticmethod
    def _interval_to_seconds(interval: str) -> int:
        """
        Convert interval string to seconds.

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

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Bybit.

        :returns: The base REST API URL.
        """
        return f"{SPOT_REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Bybit.

        :returns: The base WebSocket API URL.
        """
        return f"{SPOT_WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Bybit.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as a Bybit REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from Bybit's REST API.
        """
        # Format similar to Bybit's REST API response
        candle_data = [
            [
                str(int(c.timestamp_ms)),  # Timestamp in milliseconds
                str(c.open),  # Open price
                str(c.high),  # High price
                str(c.low),  # Low price
                str(c.close),  # Close price
                str(c.volume),  # Volume
                str(c.quote_asset_volume),  # Turnover
            ]
            for c in candles
        ]

        return {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "category": "spot",  # This will be overridden in child classes
                "symbol": trading_pair.replace("-", ""),
                "list": candle_data,
            },
            "time": int(candles[0].timestamp_ms if candles else 0),
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a Bybit WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from Bybit's WebSocket API.
        """
        interval_code = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        trading_pair_formatted = trading_pair.replace("-", "")

        # Format similar to Bybit's WebSocket API response
        return {
            "topic": f"kline.{interval_code}.{trading_pair_formatted}",
            "data": [
                {
                    "start": int(candle.timestamp_ms),
                    "end": int(candle.timestamp_ms)
                    + (
                        int(interval[:-1]) * 60 * 1000
                        if interval.endswith("m")
                        else int(interval[:-1]) * 60 * 60 * 1000
                        if interval.endswith("h")
                        else int(interval[:-1]) * 24 * 60 * 60 * 1000
                    ),
                    "interval": interval_code,
                    "open": str(candle.open),
                    "close": str(candle.close),
                    "high": str(candle.high),
                    "low": str(candle.low),
                    "volume": str(candle.volume),
                    "turnover": str(candle.quote_asset_volume),
                    "confirm": is_final,
                    "timestamp": int(candle.timestamp_ms),
                }
            ],
            "ts": int(candle.timestamp_ms),
            "type": "snapshot",
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Bybit WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions = []
        if message.get("op") == "subscribe":
            for topic in message.get("args", []):
                if topic.startswith("kline."):
                    # Format: kline.{interval}.{trading_pair}
                    parts = topic.split(".")
                    if len(parts) == 3:
                        interval_code = parts[1]
                        trading_pair = parts[2]

                        # Convert interval code back to standard format
                        interval = next(
                            (
                                k
                                for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items()
                                if v == interval_code
                            ),
                            interval_code,
                        )

                        # Convert trading pair to standard format with hyphen
                        if len(trading_pair) >= 6:  # Minimum length for a valid pair like BTCUSDT
                            # Attempt to find the split point - this is a heuristic
                            # For Bybit, we'll convert BTCUSDT to BTC-USDT
                            for i in range(1, len(trading_pair) - 2):
                                base = trading_pair[:i]
                                quote = trading_pair[i:]
                                if quote.upper() in ["USDT", "BTC", "ETH", "USD", "USDC"]:
                                    trading_pair = f"{base}-{quote}"
                                    break

                        subscriptions.append((trading_pair, interval))

        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a Bybit WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        return {
            "success": True,
            "ret_msg": "subscribe success",
            "conn_id": "mock-conn-id",
            "op": "subscribe",
            "args": message.get("args", []),
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        trading_pair_formatted = trading_pair.replace("-", "")
        interval_code = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return f"kline.{interval_code}.{trading_pair_formatted}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for Bybit candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query

        # Convert Bybit-specific parameter names to the generic ones expected by handle_klines
        symbol = params.get("symbol")
        interval = params.get("interval")
        start = params.get("start")
        end = params.get("end")
        limit = params.get("limit")

        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                limit = 1000

        # Map Bybit parameters to generic parameters expected by handle_klines
        return {
            "symbol": symbol,  # 'symbol' is the same in both
            "interval": interval,  # 'interval' is the same in both
            "start_time": start,  # 'start' in Bybit maps to 'start_time' in generic handler
            "end_time": end,  # 'end' in Bybit maps to 'end_time' in generic handler
            "limit": limit,  # 'limit' has the same name
            # Also keep the original Bybit parameter names for reference
            "category": params.get("category"),
        }

    async def handle_time(self, server, request):
        """
        Handle the Bybit time endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with server time.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        return web.json_response(
            {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "timeSecond": str(int(server._time())),
                    "timeNano": str(int(server._time() * 1e9)),
                },
                "retExtInfo": {},
                "time": int(server._time() * 1000),
            }
        )

    async def handle_klines(self, server, request):
        """
        Handle candle data request for Bybit.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: JSON response with candle data.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response(
                {"retCode": 10004, "retMsg": "Rate limit exceeded"}, status=429
            )

        # Parse parameters using our plugin method
        params = self.parse_rest_candles_params(request)

        symbol = params.get("symbol")
        interval = params.get("interval")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        limit = params.get("limit", 200)

        if not symbol or not interval:
            return web.json_response(
                {"retCode": 10001, "retMsg": "Missing required parameters"}, status=400
            )

        # Find the trading pair in our list (convert BTCUSDT to BTC-USDT)
        trading_pair = None
        for pair in server.candles:
            if pair.replace("-", "") == symbol:
                trading_pair = pair
                break

        if not trading_pair:
            return web.json_response(
                {"retCode": 10001, "retMsg": f"Invalid symbol: {symbol}"}, status=400
            )

        # Convert exchange format interval back to standard format
        standard_interval = None
        for std_int, exch_int in INTERVAL_TO_EXCHANGE_FORMAT.items():
            if exch_int == interval:
                standard_interval = std_int
                break

        if not standard_interval:
            return web.json_response(
                {"retCode": 10001, "retMsg": f"Invalid interval: {interval}"}, status=400
            )

        # Check if we have this interval
        if standard_interval not in server.candles.get(trading_pair, {}):
            return web.json_response(
                {"retCode": 10001, "retMsg": f"Invalid interval: {standard_interval}"}, status=400
            )

        # Get the candles using the standard interval format
        candles = server.candles[trading_pair][standard_interval]

        # Filter by time if specified
        if start_time:
            start_time = int(start_time)
            candles = [c for c in candles if c.timestamp_ms >= start_time]

        if end_time:
            end_time = int(end_time)
            candles = [c for c in candles if c.timestamp_ms <= end_time]

        # Apply limit
        candles = candles[-limit:] if limit > 0 else candles

        # Format response using our plugin method
        response = self.format_rest_candles(candles, trading_pair, standard_interval)
        return web.json_response(response)

    async def handle_instruments(self, server, request):
        """
        Handle instruments info request for Bybit.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: JSON response with instruments info.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response(
                {"retCode": 10004, "retMsg": "Rate limit exceeded"}, status=429
            )

        # Create instruments info from our trading pairs
        instruments = []
        for trading_pair in server.candles:
            symbol = trading_pair.replace("-", "")
            instruments.append(
                {
                    "symbol": symbol,
                    "baseCoin": trading_pair.split("-")[0],
                    "quoteCoin": trading_pair.split("-")[1],
                    "status": "Trading",
                    "minOrderQty": "0.001",
                    "maxOrderQty": "1000000",
                    "tickSize": "0.01",
                    "priceScale": 2,
                    "qtyScale": 3,
                }
            )

        return web.json_response(
            {
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "category": "spot",
                    "list": instruments,
                },
                "time": int(server._time() * 1000),
            }
        )

    async def handle_websocket(self, server, websocket, path):
        """
        Handle WebSocket connection for Bybit.

        :param server: The mock server instance.
        :param websocket: The WebSocket connection.
        :param path: The WebSocket path.
        """
        await server._handle_websocket_connection(websocket, self)
