"""
Dexalot spot plugin implementation for the mock exchange server.
"""

from datetime import UTC, datetime
from typing import Any

from aiohttp import web

from candles_feed.adapters.dexalot.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WSS_URL,
)
from candles_feed.adapters.dexalot.spot_adapter import DexalotSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.server_delegating_mixin import (
    ServerDelegatingMixin,
)

_UNIT_TO_SUFFIX = {"minute": "m", "hour": "h", "day": "d"}
_SUBSCRIBE_TYPE_PREFIX = "chart-v2-"


def _iso(timestamp: int) -> str:
    """
    Format epoch seconds the way Dexalot returns candle dates.

    :param timestamp: Epoch seconds.
    :returns: ISO 8601 UTC string with milliseconds.
    """
    return datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _iso_to_ms(value: str | None) -> int | None:
    """
    Convert an ISO 8601 string to epoch milliseconds.

    :param value: ISO 8601 string, or None.
    :returns: Epoch milliseconds, or None if no value was given.
    """
    if not value:
        return None
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


class DexalotSpotPlugin(ServerDelegatingMixin, ExchangePlugin):
    """
    Dexalot spot plugin for the mock exchange server.

    Translates between the standardized mock server format and Dexalot's candlechart
    REST response and ``chart-v2`` WebSocket protocol (ISO 8601 dates, ``BASE/QUOTE`` pairs).
    """

    def __init__(self):
        """
        Initialize the Dexalot spot plugin.
        """
        super().__init__(ExchangeType.DEXALOT_SPOT, DexalotSpotAdapter)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Dexalot.

        :returns: The base REST API URL.
        """
        return REST_URL

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Dexalot.

        :returns: The base WebSocket API URL.
        """
        return WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Dexalot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {CANDLES_ENDPOINT: ("GET", "handle_klines")}

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Dexalot.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    @staticmethod
    def _candle_dict(candle: CandleData, trading_pair: str) -> dict[str, Any]:
        """
        Build a Dexalot candle object.

        :param candle: The candle.
        :param trading_pair: The trading pair in standard format.
        :returns: The candle as returned by Dexalot's REST and WebSocket APIs.
        """
        return {
            "pair": trading_pair.replace("-", "/"),
            "date": _iso(candle.timestamp),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }

    def format_rest_candles(
        self,
        candles: list[CandleData],
        trading_pair: str,
        interval: str,
        timezone_adjustment_ms: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Format candle data as a Dexalot candlechart response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param timezone_adjustment_ms: Unused; accepted for server compatibility.
        :returns: A list of candle objects as expected from Dexalot's REST API.
        """
        return [self._candle_dict(c, trading_pair) for c in candles]

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a Dexalot ``liveCandle`` message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Unused; Dexalot sends the same shape for finished candles.
        :returns: Formatted message as expected from Dexalot's WebSocket API.
        """
        return {"type": "liveCandle", "data": [self._candle_dict(candle, trading_pair)]}

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Dexalot ``chart-v2`` (un)subscribe message.

        :param message: The message from the client.
        :returns: A list of (standard pair, standard interval) tuples.
        """
        if not str(message.get("type", "")).startswith(_SUBSCRIBE_TYPE_PREFIX):
            return []
        chart = message.get("chart", "")
        interval = next((k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == chart), chart)
        return [(str(message.get("pair", "")).replace("/", "-"), interval)]

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a Dexalot WebSocket (un)subscription acknowledgement.

        :param message: The original message.
        :param subscriptions: The (trading_pair, interval) tuples that were handled.
        :returns: The acknowledgement echoing the requested pair and chart.
        """
        return {
            "type": "subscribeResponse",
            "pair": message.get("pair"),
            "chart": message.get("chart"),
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        chart = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return f"chart-v2:{trading_pair.replace('-', '/')}:{chart}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse Dexalot candlechart request parameters.

        :param request: The web request.
        :returns: Standardized parameters (start/end times in milliseconds).
        """
        query = request.query
        suffix = _UNIT_TO_SUFFIX.get(query.get("intervalstr", ""), "")
        return {
            "symbol": query.get("pair", "").replace("/", "-"),
            "interval": f"{query.get('intervalnum', '')}{suffix}",
            "start_time": _iso_to_ms(query.get("periodfrom")),
            "end_time": _iso_to_ms(query.get("periodto")),
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }
