"""
Binance Spot plugin implementation for the mock exchange server.
"""

import time
from typing import Any

from aiohttp import web

from candles_feed.core.candle_data import CandleData
from candles_feed.testing_resources.mocks.core.exchange_plugin import ExchangePlugin
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType


class BinanceSpotPlugin(ExchangePlugin):
    """
    Binance Spot plugin for the mock exchange server.

    This plugin implements the Binance Spot API for the mock server,
    translating between the standardized mock server format and the
    Binance-specific formats.
    """

    def __init__(self, exchange_type: ExchangeType):
        """
        Initialize the Binance Spot plugin.

        :param exchange_type: The exchange type (should be ExchangeType.BINANCE_SPOT).
        """
        super().__init__(exchange_type)

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Binance Spot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/v3/ping": ("GET", "handle_ping"),
            "/api/v3/time": ("GET", "handle_time"),
            "/api/v3/klines": ("GET", "handle_klines"),
            "/api/v3/exchangeInfo": ("GET", "handle_exchange_info"),
        }

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Binance Spot.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> list[list]:
        """
        Format candle data as a Binance REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from Binance's REST API.
        """
        return [
            [
                c.timestamp_ms,  # Open time
                str(c.open),  # Open
                str(c.high),  # High
                str(c.low),  # Low
                str(c.close),  # Close
                str(c.volume),  # Volume
                c.timestamp_ms + (self._interval_to_seconds(interval) * 1000),  # Close time
                str(c.quote_asset_volume),  # Quote asset volume
                c.n_trades,  # Number of trades
                str(c.taker_buy_base_volume),  # Taker buy base asset volume
                str(c.taker_buy_quote_volume),  # Taker buy quote asset volume
                "0",  # Unused field
            ]
            for c in candles
        ]

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
        interval_seconds = self._interval_to_seconds(interval)

        return {
            "e": "kline",  # Event type
            "E": int(time.time() * 1000),  # Event time
            "s": trading_pair,  # Symbol
            "k": {
                "t": candle.timestamp_ms,  # Kline start time
                "T": candle.timestamp_ms + (interval_seconds * 1000),  # Kline close time
                "s": trading_pair,  # Symbol
                "i": interval,  # Interval
                "f": 100000000,  # First trade ID
                "L": 100000100,  # Last trade ID
                "o": str(candle.open),  # Open price
                "c": str(candle.close),  # Close price
                "h": str(candle.high),  # High price
                "l": str(candle.low),  # Low price
                "v": str(candle.volume),  # Base asset volume
                "n": candle.n_trades,  # Number of trades
                "x": is_final,  # Is this kline closed?
                "q": str(candle.quote_asset_volume),  # Quote asset volume
                "V": str(candle.taker_buy_base_volume),  # Taker buy base asset volume
                "Q": str(candle.taker_buy_quote_volume),  # Taker buy quote asset volume
            },
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Binance WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions = []

        if message.get("method") == "SUBSCRIBE":
            params = message.get("params", [])

            for channel in params:
                # Parse channel (format: symbol@kline_interval)
                parts = channel.split("@")
                if len(parts) != 2 or not parts[1].startswith("kline_"):
                    continue

                symbol = parts[0].upper()
                interval = parts[1][6:]  # Remove 'kline_' prefix

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
        return {"result": None, "id": message.get("id", 1)}

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        return f"{trading_pair.lower()}@kline_{interval}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for Binance candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query

        return {
            "symbol": params.get("symbol"),
            "interval": params.get("interval"),
            "start_time": params.get("startTime"),
            "end_time": params.get("endTime"),
            "limit": params.get("limit", "500"),
        }

    async def handle_exchange_info(self, server, request):
        """
        Handle the Binance exchangeInfo endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with exchange information.
        """
        await server._simulate_network_conditions()

        # Check rate limit
        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        # Create symbols info for all trading pairs
        symbols = []
        for trading_pair in server.trading_pairs:
            base_asset = trading_pair[:3]
            quote_asset = trading_pair[3:]

            symbols.append(
                {
                    "symbol": trading_pair,
                    "status": "TRADING",
                    "baseAsset": base_asset,
                    "baseAssetPrecision": 8,
                    "quoteAsset": quote_asset,
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
            )

        # Create exchange info response
        response = {
            "timezone": "UTC",
            "serverTime": int(time.time() * 1000),
            "rateLimits": [
                {
                    "rateLimitType": "REQUEST_WEIGHT",
                    "interval": "MINUTE",
                    "intervalNum": 1,
                    "limit": 1200,
                },
                {"rateLimitType": "ORDERS", "interval": "SECOND", "intervalNum": 10, "limit": 50},
                {"rateLimitType": "ORDERS", "interval": "DAY", "intervalNum": 1, "limit": 160000},
            ],
            "exchangeFilters": [],
            "symbols": symbols,
        }

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
        elif unit == "M":
            return value * 30 * 24 * 60 * 60
        else:
            raise ValueError(f"Unknown interval unit: {unit}")
