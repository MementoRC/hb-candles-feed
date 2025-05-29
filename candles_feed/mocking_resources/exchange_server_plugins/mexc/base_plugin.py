from abc import ABC
from typing import Any

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.mexc.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVAL_TO_PERPETUAL_FORMAT,
    PERP_REST_URL,
    PERP_WSS_URL,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class MEXCBasePlugin(ExchangePlugin, ABC):
    """
    Base class for MEXC exchange plugins.

    This class provides shared functionality for MEXC spot and perpetual plugins.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the MEXC base plugin.

        :param exchange_type: The exchange type.
        :param adapter_class: The adapter class to use.
        """
        super().__init__(exchange_type, adapter_class)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for MEXC.

        :returns: The base REST API URL.
        """
        return f"{SPOT_REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for MEXC.

        :returns: The base WebSocket API URL.
        """
        return f"{SPOT_WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for MEXC.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> list | dict:
        """
        Format candle data as a MEXC REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from MEXC's REST API.
        """
        # MEXC Spot API returns an array of candles similar to Binance
        return [
            [
                int(c.timestamp_ms),                          # Open time
                str(c.open),                                  # Open
                str(c.high),                                  # High
                str(c.low),                                   # Low
                str(c.close),                                 # Close
                str(c.volume),                                # Volume
                int(c.timestamp_ms) + self._interval_to_milliseconds(interval), # Close time
                str(c.quote_asset_volume),                    # Quote asset volume
                100,                                          # Number of trades (placeholder)
                str(c.volume * 0.7),                          # Taker buy base asset volume (placeholder)
                str(c.quote_asset_volume * 0.7),              # Taker buy quote asset volume (placeholder)
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
        elif unit == "M":
            return value * 30 * 24 * 60 * 60 * 1000
        else:
            return 60 * 1000  # Default to 1m


    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a MEXC WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from MEXC's WebSocket API.
        """
        # Format for MEXC Spot WebSocket API
        symbol = trading_pair.replace("-", "_")
        mexc_interval = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)

        return {
            "e": "push.kline",
            "d": {
                "s": symbol,                         # Symbol
                "c": str(candle.close),              # Close price
                "h": str(candle.high),               # High price
                "l": str(candle.low),                # Low price
                "o": str(candle.open),               # Open price
                "v": str(candle.volume),             # Base asset volume
                "qv": str(candle.quote_asset_volume), # Quote asset volume
                "t": int(candle.timestamp_ms),        # Kline start time
                "i": mexc_interval,                  # Interval
                "n": 100,                            # Number of trades (placeholder)
                "x": is_final                        # Is this kline closed?
            }
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a MEXC WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions = []

        # MEXC uses a method and params format similar to Binance, but with different topics
        if message.get("method") == "sub":
            for param in message.get("params", []):
                # For spot: spot@public.kline.Min1_btcusdt
                # For perp: contract@kline.Min1_btcusdt
                if "@kline." in param:
                    parts = param.split("@")
                    if len(parts) == 2:
                        topic_parts = parts[1].split(".")
                        if len(topic_parts) >= 2:
                            interval_symbol = topic_parts[-1].split("_")
                            if len(interval_symbol) == 2:
                                interval = interval_symbol[0]
                                symbol = interval_symbol[1].upper()

                                # Convert MEXC interval format to standard format
                                for std_interval, mexc_interval in INTERVAL_TO_EXCHANGE_FORMAT.items():
                                    if mexc_interval == interval:
                                        interval = std_interval
                                        break

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
        Create a MEXC WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        # Format according to MEXC WebSocket API:
        # {"channel":"push.kline","data":{"interval":"Min1","symbol":"BTC_USDT"},"symbol":"BTC_USDT"}
        if subscriptions:
            trading_pair, interval = subscriptions[0]  # Just take the first one for simplicity
            trading_pair.replace("-", "_")
            INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)

            return {
                "channel": "sub.response",
                "data": {"success": True},
                "ts": 1620000000000  # Fixed timestamp for testing
            }

        return {
            "channel": "sub.response",
            "data": {"success": False, "message": "No valid subscriptions"},
            "ts": 1620000000000  # Fixed timestamp for testing
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        # Format for internal tracking: "BTC_USDT@Min1"
        symbol = trading_pair.replace("-", "_")
        mexc_interval = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return f"{symbol}@{mexc_interval}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for MEXC candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query

        # Convert MEXC-specific parameter names to the generic ones expected by handle_klines
        symbol = params.get("symbol")
        interval = params.get("interval")
        start_time = params.get("startTime")
        end_time = params.get("endTime")
        limit = params.get("limit")

        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                limit = 500

        # Map MEXC parameters to generic parameters expected by handle_klines
        return {
            "symbol": symbol,
            "interval": interval,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,

            # Also keep the original MEXC parameter names for reference
            "startTime": start_time,
            "endTime": end_time,
        }

    async def handle_instruments(self, server, request):
        """
        Handle the MEXC instruments endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with exchange information.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        instruments = []
        for trading_pair in server.trading_pairs:
            base, quote = trading_pair.split("-", 1)
            instruments.append(
                {
                    "symbol": trading_pair.replace("-", "_"),
                    "baseAsset": base,
                    "quoteAsset": quote,
                    "pricePrecision": 8,
                    "quantityPrecision": 8,
                    "status": "ENABLED",
                }
            )

        return web.json_response({"code": 0, "data": instruments})
