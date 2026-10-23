"""
Pacifica perpetual plugin implementation for the mock exchange server.
"""

from typing import Any

from aiohttp import web

from candles_feed.adapters.pacifica.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WSS_URL,
)
from candles_feed.adapters.pacifica.perpetual_adapter import PacificaPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.server_delegating_mixin import (
    ServerDelegatingMixin,
)


class PacificaPerpetualPlugin(ServerDelegatingMixin, ExchangePlugin):
    """
    Pacifica perpetual plugin for the mock exchange server.

    Pacifica identifies markets by base asset only (``BTC``) and uses millisecond
    timestamps; WebSocket pushes are wrapped in a ``{"channel": "candle"}`` envelope.
    """

    def __init__(self):
        """
        Initialize the Pacifica perpetual plugin.
        """
        super().__init__(ExchangeType.PACIFICA_PERPETUAL, PacificaPerpetualAdapter)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Pacifica.

        :returns: The base REST API URL.
        """
        return REST_URL

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Pacifica.

        :returns: The base WebSocket API URL.
        """
        return WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Pacifica.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {CANDLES_ENDPOINT: ("GET", "handle_klines")}

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Pacifica.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    def normalize_trading_pair(self, trading_pair: str) -> str:
        """
        Convert a standard trading pair to the Pacifica symbol (base asset only).

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDC").
        :returns: Pacifica symbol (e.g., "BTC").
        """
        return PacificaPerpetualAdapter.get_trading_pair_format(trading_pair)

    @staticmethod
    def _candle_dict(candle: CandleData, trading_pair: str, interval: str) -> dict[str, Any]:
        """
        Build a Pacifica candle object.

        :param candle: The candle.
        :param trading_pair: The trading pair in standard format.
        :param interval: The candle interval.
        :returns: The candle as returned by Pacifica's REST and WebSocket APIs.
        """
        return {
            "t": int(candle.timestamp_ms),
            "T": int(candle.timestamp_ms) + INTERVALS.get(interval, 60) * 1000,
            "s": PacificaPerpetualAdapter.get_trading_pair_format(trading_pair),
            "i": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "o": str(candle.open),
            "c": str(candle.close),
            "h": str(candle.high),
            "l": str(candle.low),
            "v": str(candle.volume),
            "n": candle.n_trades,
        }

    def format_rest_candles(
        self,
        candles: list[CandleData],
        trading_pair: str,
        interval: str,
        timezone_adjustment_ms: int = 0,
    ) -> dict:
        """
        Format candle data as a Pacifica kline response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param timezone_adjustment_ms: Unused; accepted for server compatibility.
        :returns: Formatted response as expected from Pacifica's REST API.
        """
        return {
            "success": True,
            "data": [self._candle_dict(c, trading_pair, interval) for c in candles],
            "error": None,
            "code": None,
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a Pacifica ``candle`` channel push.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Unused; Pacifica sends the same shape for finished candles.
        :returns: Formatted message as expected from Pacifica's WebSocket API.
        """
        return {"channel": "candle", "data": self._candle_dict(candle, trading_pair, interval)}

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Pacifica WebSocket (un)subscribe message.

        :param message: The message from the client.
        :returns: A list of (symbol, standard interval) tuples.
        """
        params = message.get("params")
        if not isinstance(params, dict) or params.get("source") != "candle":
            return []
        code = params.get("interval", "")
        interval = next((k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == code), code)
        return [(str(params.get("symbol", "")), interval)]

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a Pacifica WebSocket (un)subscription acknowledgement.

        :param message: The original message.
        :param subscriptions: The (trading_pair, interval) tuples that were handled.
        :returns: The acknowledgement echoing the request.
        """
        return {"channel": message.get("method", "subscribe"), "data": message.get("params")}

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        symbol = PacificaPerpetualAdapter.get_trading_pair_format(trading_pair)
        return f"candle:{symbol}:{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse Pacifica kline request parameters.

        :param request: The web request.
        :returns: Standardized parameters (times are already milliseconds).
        """
        query = request.query
        code = query.get("interval", "")
        limit = query.get("limit", "")
        return {
            "symbol": query.get("symbol"),
            "interval": next(
                (k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == code), code
            ),
            "start_time": query.get("start_time"),
            "end_time": query.get("end_time"),
            "limit": int(limit) if limit.isdigit() else MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }
