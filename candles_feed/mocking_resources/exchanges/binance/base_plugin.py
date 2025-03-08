from abc import ABC
from typing import Any
from aiohttp import web
from candles_feed.adapters.base_adapter import BaseAdapter

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.adapters.binance.constants import INTERVAL_TO_EXCHANGE_FORMAT, SPOT_REST_URL, SPOT_WSS_URL


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
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query
        
        # Get all Binance klines parameters
        symbol = params.get("symbol")
        interval = params.get("interval")
        start_time = params.get("startTime")
        end_time = params.get("endTime")
        time_zone = params.get("timeZone", "0")
        limit = params.get("limit")
        
        if limit is not None:
            try:
                limit = int(limit)
                if limit > 1000:  # Binance limit is 1000
                    limit = 1000
            except ValueError:
                limit = 500  # Default limit
                
        # Parse timezone offset if provided
        timezone_offset_hours = 0
        try:
            if ":" in time_zone:
                hours, minutes = time_zone.split(":")
                timezone_offset_hours = int(hours) + (int(minutes) / 60)
            else:
                timezone_offset_hours = int(time_zone)
        except (ValueError, TypeError):
            timezone_offset_hours = 0
            
        # Map Binance parameters to generic parameters expected by handle_klines
        return {
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
        }

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

        instType = request.query.get("instType")
        if not instType:
            return web.json_response({"error": "instType is required"}, status=400)

        instruments = []
        for trading_pair in server.trading_pairs:
            base, quote = trading_pair.split("-", 1)
            instruments.append(
                {
                    "instType": instType,
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

