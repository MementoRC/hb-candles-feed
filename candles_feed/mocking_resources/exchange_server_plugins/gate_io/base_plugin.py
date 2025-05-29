from abc import ABC
from typing import Any

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.gate_io.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    REST_URL,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class GateIoBasePlugin(ExchangePlugin, ABC):
    """
    Base class for Gate.io exchange plugins.

    This class provides shared functionality for Gate.io spot and perpetual plugins.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the Gate.io base plugin.

        :param exchange_type: The exchange type.
        :param adapter_class: The adapter class to use.
        """
        super().__init__(exchange_type, adapter_class)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Gate.io.

        :returns: The base REST API URL.
        """
        return f"{REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Gate.io.

        :returns: The base WebSocket API URL.
        """
        return f"{WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Gate.io.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws/v4": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> list:
        """
        Format candle data as a Gate.io REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from Gate.io's REST API.
        """
        # Gate.io REST API candle response format:
        # [
        #   [
        #     "1626770400",  // timestamp
        #     "29932.21",    // open
        #     "30326.37",    // close
        #     "29586.26",    // low
        #     "30549.57",    // high
        #     "2501.976433", // volume
        #     "74626209.16", // quote currency volume
        #     "BTC_USDT"     // currency pair
        #   ],
        #   ...
        # ]

        formatted_candles = []
        for c in candles:
            formatted_candles.append([
                str(int(c.timestamp_ms / 1000)),  # Timestamp in seconds as string
                str(c.open),                     # Open price
                str(c.close),                    # Close price
                str(c.low),                      # Low price
                str(c.high),                     # High price
                str(c.volume),                   # Volume
                str(c.quote_asset_volume),       # Quote asset volume
                trading_pair.replace("-", "_"),  # Trading pair in Gate.io format
            ])

        return formatted_candles

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a Gate.io WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from Gate.io's WebSocket API.
        """
        # Gate.io WebSocket message format:
        # {
        #   "time": 1626770400,
        #   "channel": "spot.candlesticks",
        #   "event": "update",
        #   "result": {
        #     "t": "1626770400",      // timestamp
        #     "o": "29932.21",        // open
        #     "c": "30326.37",        // close
        #     "l": "29586.26",        // low
        #     "h": "30549.57",        // high
        #     "v": "2501.976433",     // volume
        #     "a": "74626209.16",     // quote currency volume
        #     "n": "BTC_USDT",        // currency pair
        #     "i": "1h"               // interval
        #   }
        # }

        interval_code = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        formatted_pair = trading_pair.replace("-", "_")

        channel_name = "spot.candlesticks"
        if self.exchange_type in [ExchangeType.GATE_IO_PERPETUAL]:
            channel_name = "futures.candlesticks"

        return {
            "time": int(candle.timestamp_ms / 1000),
            "channel": channel_name,
            "event": "update",
            "result": {
                "t": str(int(candle.timestamp_ms / 1000)),  # Timestamp in seconds
                "o": str(candle.open),                     # Open price
                "c": str(candle.close),                    # Close price
                "l": str(candle.low),                      # Low price
                "h": str(candle.high),                     # High price
                "v": str(candle.volume),                   # Volume
                "a": str(candle.quote_asset_volume),       # Quote asset volume
                "n": formatted_pair,                       # Currency pair
                "i": interval_code                         # Interval
            }
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Gate.io WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions = []
        if message.get("method") == "subscribe":
            params = message.get("params", [])
            if len(params) >= 2 and isinstance(params[0], str) and isinstance(params[1], dict):
                channel = params[0]
                if channel.endswith("candlesticks"):
                    pair = params[1].get("currency_pair", "").replace("_", "-")
                    interval = params[1].get("interval", "")
                    subscriptions.append((pair, interval))
        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a Gate.io WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        return {
            "id": message.get("id"),
            "result": {"status": "success"},
            "error": None
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        interval_code = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return f"{trading_pair.replace('-', '_')}_{interval_code}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for Gate.io candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query

        # Convert Gate.io-specific parameter names to the generic ones expected by handle_klines
        currency_pair = params.get("currency_pair", "").replace("_", "-")
        interval = params.get("interval")
        limit = params.get("limit")
        from_time = params.get("from")
        to_time = params.get("to")

        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                limit = 100  # Default limit for Gate.io

        # Map Gate.io parameters to generic parameters expected by handle_klines
        return {
            "symbol": currency_pair,        # 'currency_pair' in Gate.io maps to 'symbol' in generic handler
            "interval": interval,           # Same parameter name
            "start_time": from_time,        # 'from' in Gate.io maps to 'start_time' in generic handler
            "end_time": to_time,            # 'to' in Gate.io maps to 'end_time' in generic handler
            "limit": limit,                 # Same parameter name

            # Also keep the original Gate.io parameter names for reference
            "currency_pair": params.get("currency_pair"),
            "from": from_time,
            "to": to_time,
        }

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
