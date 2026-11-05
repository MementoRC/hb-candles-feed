"""
Aevo perpetual plugin implementation for the mock exchange server.

Aevo only exposes mark-price history, so candles are served as ``[timestamp_ns, price]``
pairs (the close price) and live updates as 500 ms ticker messages.
"""

from typing import Any

from aiohttp import web

from candles_feed.adapters.aevo.constants import (
    INTERVAL_TO_EXCHANGE,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WSS_URL,
)
from candles_feed.adapters.aevo.perpetual_adapter import AevoPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.server_delegating_mixin import (
    ServerDelegatingMixin,
)

_NS_PER_MS = 1_000_000
_TICKER_PREFIX = "ticker-500ms:"
# Ticker subscriptions carry no interval; this is the one the mock serves them for.
_TICKER_INTERVAL = "1m"


class AevoPerpetualPlugin(ServerDelegatingMixin, ExchangePlugin):
    """
    Aevo perpetual plugin for the mock exchange server.

    Translates between the standardized mock server format and Aevo's mark-history
    REST response and ticker WebSocket channel.
    """

    def __init__(self):
        """
        Initialize the Aevo perpetual plugin.
        """
        super().__init__(ExchangeType.AEVO_PERPETUAL, AevoPerpetualAdapter)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Aevo.

        :returns: The base REST API URL.
        """
        return REST_URL

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Aevo.

        :returns: The base WebSocket API URL.
        """
        return WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Aevo.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {"/mark-history": ("GET", "handle_klines")}

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Aevo.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    def normalize_trading_pair(self, trading_pair: str) -> str:
        """
        Convert a standard trading pair to the Aevo instrument name.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDC").
        :returns: Aevo instrument name (e.g., "BTC-PERP").
        """
        return AevoPerpetualAdapter.get_trading_pair_format(trading_pair)

    def format_rest_candles(
        self,
        candles: list[CandleData],
        trading_pair: str,
        interval: str,
        timezone_adjustment_ms: int = 0,
    ) -> dict:
        """
        Format candle data as an Aevo mark-history response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param timezone_adjustment_ms: Unused; accepted for server compatibility.
        :returns: Formatted response as expected from Aevo's REST API.
        """
        return {"history": [[str(int(c.timestamp_ms) * _NS_PER_MS), str(c.close)] for c in candles]}

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as an Aevo ticker message carrying the mark price.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Unused; tickers have no finality flag.
        :returns: Formatted message as expected from Aevo's WebSocket API.
        """
        timestamp_ns = int(candle.timestamp_ms) * _NS_PER_MS
        return {
            "channel": f"{_TICKER_PREFIX}{self.normalize_trading_pair(trading_pair)}",
            "timestamp": timestamp_ns,
            "data": {"timestamp": timestamp_ns, "mark_price": str(candle.close)},
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse an Aevo WebSocket (un)subscribe message.

        :param message: The message from the client.
        :returns: (instrument name, interval) tuples; the interval is fixed because
            ticker subscriptions do not carry one.
        """
        return [
            (channel.removeprefix(_TICKER_PREFIX), _TICKER_INTERVAL)
            for channel in message.get("data", [])
            if isinstance(channel, str) and channel.startswith(_TICKER_PREFIX)
        ]

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create an Aevo WebSocket subscription acknowledgement.

        :param message: The original message.
        :param subscriptions: The (trading_pair, interval) tuples that were subscribed to.
        :returns: The acknowledgement listing the subscribed channels.
        """
        return {"data": [f"{_TICKER_PREFIX}{pair}" for pair, _ in subscriptions]}

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval (not part of the key; tickers have none).
        :returns: The ticker channel name.
        """
        return f"{_TICKER_PREFIX}{self.normalize_trading_pair(trading_pair)}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse Aevo mark-history request parameters.

        :param request: The web request.
        :returns: Standardized parameters (start_time in milliseconds).
        """
        query = request.query
        resolution = query.get("resolution", "")
        start_ns = query.get("start_timestamp")
        limit = query.get("limit", "")
        return {
            "symbol": query.get("instrument_name"),
            "interval": next(
                (k for k, v in INTERVAL_TO_EXCHANGE.items() if str(v) == resolution), resolution
            ),
            "start_time": int(start_ns) // _NS_PER_MS if start_ns else None,
            "end_time": None,
            "limit": int(limit) if limit.isdigit() else MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }
