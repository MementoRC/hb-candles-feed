"""
Base class for KuCoin exchange plugins.

This class provides shared functionality for KuCoin spot and perpetual plugins.
"""

from abc import ABC
from typing import Any

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.kucoin.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class KucoinBasePlugin(ExchangePlugin, ABC):
    """
    Base class for KuCoin exchange plugins.

    This class provides shared functionality for KuCoin spot and perpetual plugins.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the KuCoin base plugin.

        :param exchange_type: The exchange type.
        :param adapter_class: The adapter class for this exchange.
        """
        super().__init__(exchange_type, adapter_class)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for KuCoin.

        :returns: The base REST API URL.
        """
        return f"{REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for KuCoin.

        :returns: The base WebSocket API URL.
        """
        return f"{SPOT_WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for KuCoin.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as a KuCoin REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from KuCoin's REST API.
        """
        # Format similar to KuCoin's REST API response
        candle_data = [
            [
                int(c.timestamp_ms),              # Timestamp in milliseconds
                str(c.open),                      # Open price
                str(c.close),                     # Close price
                str(c.high),                      # High price
                str(c.low),                       # Low price
                str(c.volume),                    # Volume
                str(c.quote_asset_volume)         # Quote volume
            ]
            for c in candles
        ]

        return {
            "code": "200000",
            "data": candle_data
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a KuCoin WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from KuCoin's WebSocket API.
        """
        interval_code = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)

        # Format similar to KuCoin's WebSocket API response
        return {
            "type": "message",
            "topic": f"/market/candles:{trading_pair}_{interval_code}",
            "subject": "trade.candles.update",
            "data": {
                "symbol": trading_pair,
                "candles": [
                    str(int(candle.timestamp_ms)),   # Timestamp in milliseconds
                    str(candle.open),                # Open price
                    str(candle.close),               # Close price
                    str(candle.high),                # High price
                    str(candle.low),                 # Low price
                    str(candle.volume),              # Volume
                    str(candle.quote_asset_volume)   # Quote volume
                ],
                "time": int(candle.timestamp_ms)
            }
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a KuCoin WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions = []
        if message.get("type") == "subscribe":
            topics = message.get("topic", "").split(",")
            for topic in topics:
                if topic.startswith("/market/candles:"):
                    # Format: /market/candles:{trading_pair}_{interval}
                    parts = topic[16:].split("_")  # Remove "/market/candles:" prefix
                    if len(parts) == 2:
                        trading_pair = parts[0]
                        interval_code = parts[1]

                        # Convert interval code back to standard format
                        interval = next((k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == interval_code), interval_code)

                        subscriptions.append((trading_pair, interval))

        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a KuCoin WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        return {
            "id": message.get("id", "mock-id"),
            "type": "ack"
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        interval_code = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return f"/market/candles:{trading_pair}_{interval_code}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for KuCoin candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query

        # Convert KuCoin-specific parameter names to the generic ones expected by handle_klines
        symbol = params.get("symbol")
        interval = params.get("type", "1min")
        start_time = params.get("startAt")
        end_time = params.get("endAt")

        # KuCoin may have a limit parameter
        limit = params.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                limit = 100  # Default limit

        # Map KuCoin parameters to generic parameters expected by handle_klines
        return {
            "symbol": symbol,
            "interval": next((k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == interval), interval),
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }

    async def handle_time(self, server, request):
        """
        Handle the KuCoin time endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with server time.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"code": "429000", "msg": "Rate limit exceeded"}, status=429)

        return web.json_response({
            "code": "200000",
            "data": int(server._time() * 1000)
        })
