from abc import ABC
from typing import Any

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.okx.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class OKXBasePlugin(ExchangePlugin, ABC):
    """
    Base class for OKX exchange plugins.

    This class provides shared functionality for OKX spot and perpetual plugins.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the OKX base plugin.

        :param exchange_type: The exchange type.
        """
        super().__init__(exchange_type, adapter_class)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for OKX.

        :returns: The base REST API URL.
        """
        return f"{SPOT_REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for OKX.

        :returns: The base WebSocket API URL.
        """
        return f"{SPOT_WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for OKX.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws/v5/public": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as an OKX REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from OKX's REST API.
        """
        # OKX REST API candle response format:
        # {
        #   "code": "0",
        #   "msg": "",
        #   "data": [
        #     [
        #       "1597026383085",  // timestamp
        #       "11520.2",        // open
        #       "11520.5",        // high
        #       "11520.2",        // low
        #       "11520.3",        // close
        #       "0.0021",         // volume
        #       "24.198",         // quote asset volume
        #     ]
        #   ]
        # }

        return {
            "code": "0",
            "msg": "",
            "data": [
                [
                    str(int(c.timestamp_ms)),  # Timestamp in milliseconds as string
                    str(c.open),  # Open price
                    str(c.high),  # High price
                    str(c.low),  # Low price
                    str(c.close),  # Close price
                    str(c.volume),  # Volume
                    str(c.quote_asset_volume),  # Quote asset volume
                ]
                for c in candles
            ],
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as an OKX WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from OKX's WebSocket API.
        """
        # OKX WebSocket message format:
        # {
        #   "arg": {
        #     "channel": "candle1m",
        #     "instId": "BTC-USDT"
        #   },
        #   "data": [
        #     [
        #       "1597026383085", // ts
        #       "11520.2",       // o
        #       "11520.5",       // h
        #       "11520.2",       // l
        #       "11520.3",       // c
        #       "0.0021",        // vol
        #       "24.198"         // volCcy
        #     ]
        #   ]
        # }

        # OKX uses candle{interval} format
        interval_code = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)

        return {
            "arg": {"channel": f"candle{interval_code}", "instId": trading_pair},
            "data": [
                [
                    str(int(candle.timestamp_ms)),  # Timestamp in milliseconds as string
                    str(candle.open),  # Open price
                    str(candle.high),  # High price
                    str(candle.low),  # Low price
                    str(candle.close),  # Close price
                    str(candle.volume),  # Volume
                    str(candle.quote_asset_volume),  # Quote asset volume
                ]
            ],
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse an OKX WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions = []
        if message.get("op") == "subscribe":
            subscriptions.extend(
                (arg["instId"], arg["channel"][6:])
                for arg in message.get("args", [])
                if arg.get("channel", "").startswith("candle") and arg.get("instId")
            )
        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create an OKX WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        return {"event": "subscribe", "arg": message["args"][0], "code": "0", "msg": "OK"}

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        # Format matching OKX's subscription format
        interval_code = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return f"candle{interval_code}_{trading_pair}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for OKX candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query

        # Convert OKX-specific parameter names to the generic ones expected by handle_klines
        inst_id = params.get("instId")
        bar = params.get("bar")
        after = params.get("after")
        before = params.get("before")
        limit = params.get("limit")

        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                limit = 500

        # Map OKX parameters to generic parameters expected by handle_klines
        return {
            "symbol": inst_id,  # 'instId' in OKX maps to 'symbol' in generic handler
            "interval": bar,  # 'bar' in OKX maps to 'interval' in generic handler
            "start_time": after,  # 'after' in OKX maps to 'start_time' in generic handler
            "end_time": before,  # 'before' in OKX maps to 'end_time' in generic handler
            "limit": limit,  # 'limit' has the same name
            # Also keep the original OKX parameter names for reference
            "instId": inst_id,
            "bar": bar,
            "after": after,
            "before": before,
        }

    async def handle_instruments(self, server, request):
        """
        Handle the OKX instruments endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with exchange information.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        inst_type_query = request.query.get("instType")
        if not inst_type_query:
            return web.json_response({"error": "instType is required"}, status=400)

        instruments = []
        for trading_pair in server.trading_pairs:
            base, quote = trading_pair.split("-", 1)
            instruments.append(
                {
                    "instType": inst_type_query,
                    "instId": trading_pair.replace("-", "/"),
                    "uly": trading_pair,
                    "baseCcy": base,
                    "quoteCcy": quote,
                    "settleCcy": quote,
                    "ctValCcy": quote,
                    "optType": "C",  # or "P" for put options
                    "stk": trading_pair,
                    "listTime": int(server._time() * 1000),
                    "expTime": int(server._time() * 1000)
                    + 3600 * 24 * 30 * 1000,  # 30 days from now
                    "lever": "10",
                    "tickSz": "0.01",
                    "lotSz": "1",
                    "minSz": "1",
                    "ctVal": "1",
                    "state": "live",
                }
            )

        response = {"code": "0", "msg": "", "data": instruments}
        return web.json_response(response)

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
