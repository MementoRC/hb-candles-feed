"""
Bitmart perpetual plugin implementation for the mock exchange server.
"""

from typing import Any

from aiohttp import web

from candles_feed.adapters.bitmart.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_REST,
    INTERVAL_TO_EXCHANGE_WS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WSS_URL,
)
from candles_feed.adapters.bitmart.perpetual_adapter import BitmartPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.server_delegating_mixin import (
    ServerDelegatingMixin,
)

_GROUP_PREFIX = "futures/klineBin"


class BitmartPerpetualPlugin(ServerDelegatingMixin, ExchangePlugin):
    """
    Bitmart perpetual plugin for the mock exchange server.

    Translates between the standardized mock server format and Bitmart's futures kline
    REST response (object rows, seconds) and ``futures/klineBin`` WebSocket groups.
    """

    def __init__(self):
        """
        Initialize the Bitmart perpetual plugin.
        """
        super().__init__(ExchangeType.BITMART_PERPETUAL, BitmartPerpetualAdapter)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Bitmart.

        :returns: The base REST API URL.
        """
        return REST_URL

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Bitmart.

        :returns: The base WebSocket API URL.
        """
        return WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Bitmart.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {CANDLES_ENDPOINT: ("GET", "handle_klines")}

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Bitmart.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    def format_rest_candles(
        self,
        candles: list[CandleData],
        trading_pair: str,
        interval: str,
        timezone_adjustment_ms: int = 0,
    ) -> dict:
        """
        Format candle data as a Bitmart futures kline response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param timezone_adjustment_ms: Unused; accepted for server compatibility.
        :returns: Formatted response as expected from Bitmart's REST API.
        """
        return {
            "code": 1000,
            "message": "Ok",
            "data": [
                {
                    "timestamp": int(c.timestamp),
                    "open_price": str(c.open),
                    "high_price": str(c.high),
                    "low_price": str(c.low),
                    "close_price": str(c.close),
                    "volume": str(c.volume),
                }
                for c in candles
            ],
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a Bitmart ``futures/klineBin`` message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Unused; Bitmart sends the same shape for finished candles.
        :returns: Formatted message as expected from Bitmart's WebSocket API.
        """
        return {
            "group": self.create_ws_subscription_key(trading_pair, interval),
            "data": {
                "symbol": trading_pair.replace("-", ""),
                "items": [
                    {
                        "ts": int(candle.timestamp),
                        "o": candle.open,
                        "h": candle.high,
                        "l": candle.low,
                        "c": candle.close,
                        "v": candle.volume,
                    }
                ],
            },
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Bitmart WebSocket (un)subscribe message.

        :param message: The message from the client.
        :returns: A list of (symbol, standard interval) tuples.
        """
        subscriptions: list[tuple[str, str]] = []
        for arg in message.get("args", []):
            head, _, symbol = str(arg).partition(":")
            if head.startswith(_GROUP_PREFIX) and symbol:
                code = head.removeprefix(_GROUP_PREFIX)
                interval = next((k for k, v in INTERVAL_TO_EXCHANGE_WS.items() if v == code), code)
                subscriptions.append((symbol, interval))
        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a Bitmart WebSocket (un)subscription acknowledgement.

        :param message: The original message.
        :param subscriptions: The (trading_pair, interval) tuples that were handled.
        :returns: The acknowledgement echoing the first requested group.
        """
        args = message.get("args") or [""]
        return {"action": message.get("action", "subscribe"), "group": args[0], "success": True}

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: The Bitmart group name, e.g. ``futures/klineBin1m:BTCUSD``.
        """
        code = INTERVAL_TO_EXCHANGE_WS.get(interval, interval)
        return f"{_GROUP_PREFIX}{code}:{trading_pair.replace('-', '')}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse Bitmart kline request parameters.

        :param request: The web request.
        :returns: Standardized parameters (start/end times converted to milliseconds).
        """
        query = request.query
        step = query.get("step", "")
        start, end = query.get("start_time"), query.get("end_time")
        return {
            "symbol": query.get("symbol"),
            "interval": next(
                (k for k, v in INTERVAL_TO_EXCHANGE_REST.items() if str(v) == step), step
            ),
            "start_time": int(start) * 1000 if start else None,
            "end_time": int(end) * 1000 if end else None,
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }
