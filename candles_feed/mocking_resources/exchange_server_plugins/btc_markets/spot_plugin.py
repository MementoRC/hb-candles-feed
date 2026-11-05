"""
BTC Markets spot plugin implementation for the mock exchange server.

BTC Markets has no candle WebSocket, so this plugin serves REST only and exposes no
WebSocket routes.
"""

from datetime import UTC, datetime
from typing import Any

from aiohttp import web

from candles_feed.adapters.btc_markets.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
)
from candles_feed.adapters.btc_markets.spot_adapter import BTCMarketsSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.server_delegating_mixin import (
    ServerDelegatingMixin,
)


class BTCMarketsSpotPlugin(ServerDelegatingMixin, ExchangePlugin):
    """
    BTC Markets spot plugin for the mock exchange server.

    The market id is part of the URL path (``/v3/markets/{market_id}/candles``) and
    candles are arrays whose first element is an ISO 8601 timestamp.
    """

    def __init__(self):
        """
        Initialize the BTC Markets spot plugin.
        """
        super().__init__(ExchangeType.BTC_MARKETS_SPOT, BTCMarketsSpotAdapter)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for BTC Markets.

        :returns: The base REST API URL.
        """
        return REST_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for BTC Markets.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        # The endpoint's "{market_id}" placeholder doubles as an aiohttp dynamic route segment.
        return {CANDLES_ENDPOINT: ("GET", "handle_klines")}

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes; BTC Markets has no candle WebSocket.

        :returns: An empty dictionary.
        """
        return {}

    def format_rest_candles(
        self,
        candles: list[CandleData],
        trading_pair: str,
        interval: str,
        timezone_adjustment_ms: int = 0,
    ) -> list[list[str]]:
        """
        Format candle data as a BTC Markets candles response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param timezone_adjustment_ms: Unused; accepted for server compatibility.
        :returns: ``[iso timestamp, open, high, low, close, volume]`` rows of strings.
        """
        return [
            [
                datetime.fromtimestamp(c.timestamp, UTC).strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
                str(c.open),
                str(c.high),
                str(c.low),
                str(c.close),
                str(c.volume),
            ]
            for c in candles
        ]

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> Any:
        """
        BTC Markets has no candle WebSocket.

        :raises NotImplementedError: Always.
        """
        raise NotImplementedError("BTC Markets does not support WebSocket candles")

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        BTC Markets has no candle WebSocket, so nothing can be subscribed to.

        :param message: The message from the client.
        :returns: An empty list.
        """
        return []

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        BTC Markets has no candle WebSocket, so there is nothing to acknowledge.

        :param message: The original message.
        :param subscriptions: The subscriptions that were handled.
        :returns: An empty dictionary.
        """
        return {}

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a key for internal tracking (never used for live subscriptions).

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key.
        """
        return f"{trading_pair}_{interval}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse BTC Markets candle request parameters.

        :param request: The web request; the market id comes from the URL path.
        :returns: Standardized parameters (start_time in milliseconds).
        """
        query = request.query
        window = query.get("timeWindow", "")
        start = query.get("from")
        limit = query.get("limit", "")
        return {
            "symbol": request.match_info.get("market_id"),
            "interval": next(
                (k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == window), window
            ),
            "start_time": (
                int(datetime.fromisoformat(start.replace("Z", "+00:00")).timestamp() * 1000)
                if start
                else None
            ),
            "end_time": None,
            "limit": int(limit) if limit.isdigit() else MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }
