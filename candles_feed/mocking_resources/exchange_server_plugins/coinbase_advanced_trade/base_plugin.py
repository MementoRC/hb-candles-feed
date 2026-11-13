"""
Base class for Coinbase Advanced Trade exchange plugins.

This class provides shared functionality for Coinbase Advanced Trade plugins.
"""

from abc import ABC
from datetime import UTC, datetime
from typing import Any

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.coinbase_advanced_trade.constants import (
    INTERVAL_TO_GRANULARITY,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.server_delegating_mixin import (
    ServerDelegatingMixin,
)

_GRANULARITY_TO_INTERVAL = {v: k for k, v in INTERVAL_TO_GRANULARITY.items()}
_QUOTE_SUFFIXES = ("USDT", "USDC", "USD", "EUR", "GBP", "BTC", "ETH")


class CoinbaseAdvancedTradeBasePlugin(ServerDelegatingMixin, ExchangePlugin, ABC):
    """
    Base class for Coinbase Advanced Trade exchange plugins.

    This class provides shared functionality for Coinbase Advanced Trade plugins.
    Candle lookup and subscription bookkeeping are delegated to the mock server.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the Coinbase Advanced Trade base plugin.

        :param exchange_type: The exchange type.
        :param adapter_class: The adapter class for this exchange.
        """
        super().__init__(exchange_type, adapter_class)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Coinbase Advanced Trade.

        :returns: The base REST API URL.
        """
        return f"{SPOT_REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Coinbase Advanced Trade.

        :returns: The base WebSocket API URL.
        """
        return f"{SPOT_WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Coinbase Advanced Trade.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/": "handle_websocket"}

    def normalize_trading_pair(self, trading_pair: str) -> str:
        """
        Normalize a trading pair to Coinbase's ``BASE-QUOTE`` product id.

        Pairs registered without a separator (e.g. "BTCUSD") get one inserted before
        the quote currency.

        :param trading_pair: The trading pair, with or without separator.
        :returns: The upper-case product id (e.g. "BTC-USD").
        """
        pair = trading_pair.upper()
        if "-" in pair:
            return pair
        for quote in _QUOTE_SUFFIXES:
            if pair.endswith(quote) and len(pair) > len(quote):
                return f"{pair[: -len(quote)]}-{quote}"
        return pair

    def format_rest_candles(
        self,
        candles: list[CandleData],
        trading_pair: str,
        interval: str,
        timezone_adjustment_ms: int = 0,
    ) -> dict:
        """
        Format candle data as a Coinbase Advanced Trade REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param timezone_adjustment_ms: Unused; accepted for server compatibility.
        :returns: Formatted response as expected from Coinbase Advanced Trade's REST API.
        """
        # Format according to Coinbase REST API candle response (all values are strings,
        # `start` is UNIX seconds, newest candle first):
        # {
        #   "candles": [
        #     {
        #       "start": "1639508050",
        #       "low": "29288.38",
        #       "high": "29477.29",
        #       "open": "29405.34",
        #       "close": "29374.47",
        #       "volume": "142.0450069"
        #     },
        #     ...
        #   ]
        # }
        return {"candles": [self._candle_dict(c) for c in reversed(candles)]}

    @staticmethod
    def _candle_dict(candle: CandleData) -> dict[str, str]:
        """
        Build the Coinbase candle object shared by REST and WebSocket payloads.

        :param candle: Candle data to format.
        :returns: The candle as a dict of strings.
        """
        return {
            "start": str(int(candle.timestamp)),
            "low": str(candle.low),
            "high": str(candle.high),
            "open": str(candle.open),
            "close": str(candle.close),
            "volume": str(candle.volume),
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a Coinbase Advanced Trade WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from Coinbase Advanced Trade's WebSocket API.
        """
        # Format according to Coinbase WS candle format:
        # {
        #   "channel": "candles",
        #   "client_id": "",
        #   "timestamp": "2023-02-14T17:02:36.346Z",
        #   "sequence_num": 1234,
        #   "events": [
        #     {
        #       "type": "snapshot" | "update",
        #       "candles": [
        #         {
        #           "start": "1676394060",
        #           "high": "22540.7", "low": "22537.4", "open": "22537.4",
        #           "close": "22540.7", "volume": "0.1360142", "product_id": "BTC-USD"
        #         }
        #       ]
        #     }
        #   ]
        # }
        current_time_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        return {
            "channel": "candles",
            "client_id": "",
            "timestamp": current_time_iso,
            "sequence_num": int(candle.timestamp * 1000) % 100000,
            "events": [
                {
                    "type": "update",
                    "candles": [
                        {
                            **self._candle_dict(candle),
                            "product_id": self.normalize_trading_pair(trading_pair),
                        }
                    ],
                }
            ],
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Coinbase Advanced Trade WebSocket subscription message.

        The candles channel has no granularity option; it is fixed at 5 minutes.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        # Coinbase subscription format:
        # {
        #   "type": "subscribe",
        #   "channel": "candles",
        #   "product_ids": ["BTC-USD"]
        # }
        if (
            isinstance(message, dict)
            and message.get("type") in ("subscribe", "unsubscribe")
            and message.get("channel") == "candles"
        ):
            return [(product_id, WS_INTERVALS[0]) for product_id in message.get("product_ids", [])]
        return []

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a Coinbase Advanced Trade WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        # Coinbase subscription success format:
        # {
        #   "channel": "subscriptions",
        #   "events": [{"subscriptions": {"candles": ["BTC-USD"]}}]
        # }
        return {
            "channel": "subscriptions",
            "client_id": "",
            "events": [{"subscriptions": {"candles": [tp for tp, _ in subscriptions]}}],
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        return f"candles_{self.normalize_trading_pair(trading_pair)}_{interval}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for Coinbase Advanced Trade candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names (times in milliseconds).
        """
        query = request.query
        granularity = query.get("granularity", "")
        interval = _GRANULARITY_TO_INTERVAL.get(granularity)
        if interval is None:
            return {
                "valid": False,
                "error": {"message": f"Invalid granularity: {granularity!r}"},
            }

        params: dict[str, Any] = {
            "symbol": request.match_info.get("product_id"),
            "interval": interval,
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

        limit = query.get("limit", "")
        if limit.isdigit():
            params["limit"] = min(int(limit), MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST)

        # start/end are UNIX seconds; the server compares milliseconds
        for key, name in (("start", "start_time"), ("end", "end_time")):
            value = query.get(key, "")
            if value.isdigit():
                params[name] = int(value) * 1000

        return params

    async def handle_products(self, server, request):
        """
        Handle the Coinbase Advanced Trade products endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with product information.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        products = []
        for trading_pair in server.trading_pairs:
            product_id = self.normalize_trading_pair(trading_pair)
            base, quote = product_id.split("-", 1)
            products.append(
                {
                    "product_id": product_id,
                    "price": str(server.trading_pairs[trading_pair]),
                    "price_percentage_change_24h": "0.0",
                    "volume_24h": "1000.0",
                    "base_increment": "0.00000001",
                    "quote_increment": "0.01",
                    "quote_min_size": "1.0",
                    "quote_max_size": "10000.0",
                    "base_min_size": "0.0001",
                    "base_max_size": "10000.0",
                    "base_name": base,
                    "quote_name": quote,
                    "status": "online",
                    "cancel_only": False,
                    "limit_only": False,
                    "post_only": False,
                    "trading_disabled": False,
                }
            )

        return web.json_response({"products": products})

    async def handle_time(self, server, request):
        """
        Handle the Coinbase Advanced Trade time endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with server time.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        current_time = datetime.fromtimestamp(server._time(), tz=UTC)
        iso_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3]

        return web.json_response({"iso": iso_time, "epoch": server._time()})
