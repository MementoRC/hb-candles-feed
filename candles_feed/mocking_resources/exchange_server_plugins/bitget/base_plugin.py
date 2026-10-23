"""
Base class for Bitget exchange plugins.

This class provides shared functionality for Bitget spot and perpetual plugins.
"""

import time
from abc import ABC
from typing import Any

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.bitget.constants import (
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_REST_URL,
    WS_INTERVAL_TO_EXCHANGE,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.server_delegating_mixin import (
    ServerDelegatingMixin,
)


def _standard_interval(mapping: dict[str, str], exchange_interval: str) -> str:
    """
    Convert an exchange interval code back to the standard interval name.

    :param mapping: Standard interval -> exchange interval code.
    :param exchange_interval: The exchange interval code.
    :returns: The standard interval, or the code itself if unknown.
    """
    return next((k for k, v in mapping.items() if v == exchange_interval), exchange_interval)


class BitgetBasePlugin(ServerDelegatingMixin, ExchangePlugin, ABC):
    """
    Base class for Bitget exchange plugins.

    Subclasses set the REST interval mapping, the WebSocket ``instType`` and the routes.
    """

    def __init__(
        self,
        exchange_type: ExchangeType,
        adapter_class: type[BaseAdapter],
        rest_interval_map: dict[str, str],
        inst_type: str,
    ):
        """
        Initialize the Bitget base plugin.

        :param exchange_type: The exchange type.
        :param adapter_class: The adapter class for this exchange.
        :param rest_interval_map: Standard interval -> REST ``granularity`` code.
        :param inst_type: ``instType`` used in WebSocket ``arg`` objects.
        """
        super().__init__(exchange_type, adapter_class)
        self._rest_interval_map = rest_interval_map
        self._inst_type = inst_type

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Bitget.

        :returns: The base REST API URL.
        """
        return SPOT_REST_URL

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Bitget.

        :returns: The base WebSocket API URL.
        """
        return WSS_URL

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Bitget.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    @staticmethod
    def _candle_row(candle: CandleData) -> list[str]:
        """
        Build the 7-column Bitget candle row.

        :param candle: The candle.
        :returns: ``[ts_ms, open, high, low, close, base volume, quote volume]`` as strings.
        """
        return [
            str(int(candle.timestamp_ms)),
            str(candle.open),
            str(candle.high),
            str(candle.low),
            str(candle.close),
            str(candle.volume),
            str(candle.quote_asset_volume),
        ]

    def format_rest_candles(
        self,
        candles: list[CandleData],
        trading_pair: str,
        interval: str,
        timezone_adjustment_ms: int = 0,
    ) -> dict:
        """
        Format candle data as a Bitget REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param timezone_adjustment_ms: Unused; accepted for server compatibility.
        :returns: Formatted response as expected from Bitget's REST API.
        """
        return {
            "code": "00000",
            "msg": "success",
            "requestTime": int(time.time() * 1000),
            "data": [self._candle_row(c) for c in candles],
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a Bitget WebSocket candle update.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Unused; Bitget sends the same update shape for finished candles.
        :returns: Formatted message as expected from Bitget's WebSocket API.
        """
        return {
            "action": "update",
            "arg": {
                "instType": self._inst_type,
                "channel": f"candle{WS_INTERVAL_TO_EXCHANGE.get(interval, interval)}",
                "instId": trading_pair.replace("-", ""),
            },
            "data": [self._candle_row(candle)],
            "ts": int(candle.timestamp_ms),
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Bitget WebSocket (un)subscribe message.

        :param message: The message from the client.
        :returns: A list of (instId, standard interval) tuples.
        """
        subscriptions: list[tuple[str, str]] = []
        for arg in message.get("args", []):
            channel = arg.get("channel", "") if isinstance(arg, dict) else ""
            if channel.startswith("candle") and arg.get("instId"):
                interval = _standard_interval(
                    WS_INTERVAL_TO_EXCHANGE, channel.removeprefix("candle")
                )
                subscriptions.append((arg["instId"], interval))
        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a Bitget WebSocket (un)subscription acknowledgement.

        :param message: The original message.
        :param subscriptions: The (trading_pair, interval) tuples that were handled.
        :returns: The acknowledgement echoing the first requested channel.
        """
        args = message.get("args") or [{}]
        event = "unsubscribe" if "unsub" in str(message.get("op", "")) else "subscribe"
        return {"event": event, "arg": args[0]}

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        channel = f"candle{WS_INTERVAL_TO_EXCHANGE.get(interval, interval)}"
        return f"{self._inst_type}:{channel}:{trading_pair.replace('-', '')}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse Bitget candle request parameters.

        :param request: The web request.
        :returns: Standardized parameters (start/end times in milliseconds).
        """
        query = request.query
        limit = query.get("limit", "")
        return {
            "symbol": query.get("symbol"),
            "interval": _standard_interval(self._rest_interval_map, query.get("granularity", "")),
            "start_time": query.get("startTime"),
            "end_time": query.get("endTime"),
            "limit": int(limit) if limit.isdigit() else MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }
