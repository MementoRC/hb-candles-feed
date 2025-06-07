import json  # Add this import
from abc import ABC
from typing import Any

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.hyperliquid.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    REST_URL,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class HyperliquidBasePlugin(ExchangePlugin, ABC):
    """
    Base class for HyperLiquid exchange plugins.

    This class provides shared functionality for HyperLiquid spot and perpetual plugins.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the HyperLiquid base plugin.

        :param exchange_type: The exchange type.
        :param adapter_class: The adapter class to use.
        """
        super().__init__(exchange_type, adapter_class)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for HyperLiquid.

        :returns: The base REST API URL.
        """
        return f"{REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for HyperLiquid.

        :returns: The base WebSocket API URL.
        """
        return f"{WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for HyperLiquid.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> list:
        """
        Format candle data as a HyperLiquid REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from HyperLiquid's REST API.
        """
        # HyperLiquid returns an array of candles directly, with format:
        # [
        #   [timestamp, open, high, low, close, volume, quoteVolume],
        #   ...
        # ]
        return [
            [
                int(c.timestamp),  # Timestamp (in seconds)
                float(c.open),  # Open
                float(c.high),  # High
                float(c.low),  # Low
                float(c.close),  # Close
                float(c.volume),  # Volume
                float(c.quote_asset_volume),  # Quote asset volume
            ]
            for c in candles
        ]

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a HyperLiquid WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from HyperLiquid's WebSocket API.
        """
        # Format for HyperLiquid WebSocket API:
        # {
        #   "channel": "candles",
        #   "coin": "BTC",
        #   "interval": "1",
        #   "data": [timestamp, open, high, low, close, volume, quoteVolume]
        # }

        coin = trading_pair.split("-")[0]  # Get base asset from trading pair

        return {
            "channel": "candles",
            "coin": coin,
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "data": [
                int(candle.timestamp),  # Timestamp (in seconds)
                float(candle.open),  # Open
                float(candle.high),  # High
                float(candle.low),  # Low
                float(candle.close),  # Close
                float(candle.volume),  # Volume
                float(candle.quote_asset_volume),  # Quote asset volume
            ],
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a HyperLiquid WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions = []

        # HyperLiquid uses a subscription format:
        # {
        #   "method": "subscribe",
        #   "channel": "candles",
        #   "coin": "BTC",
        #   "interval": "1"
        # }

        if message.get("method") == "subscribe" and message.get("channel") == "candles":
            coin = message.get("coin")
            interval = message.get("interval")

            if coin and interval:
                # Convert exchange interval format to standardized format
                standardized_interval = next(
                    (k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == interval), interval
                )

                # Convert coin to standardized trading pair format (adding -USDT)
                standardized_trading_pair = f"{coin}-USDT"

                subscriptions.append((standardized_trading_pair, standardized_interval))

        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a HyperLiquid WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        # HyperLiquid subscription success response:
        # {
        #   "success": True,
        #   "message": "Subscription successful"
        # }
        return {"success": True, "message": "Subscription successful"}

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        # Format according to HyperLiquid: "BTC:1"
        coin = trading_pair.split("-")[0]
        exchange_interval = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return f"{coin}:{exchange_interval}"

    async def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:  # type: ignore[override]
        """
        Parse REST API parameters for HyperLiquid candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        # HyperLiquid uses POST with JSON body
        try:
            data = await request.json()
        except json.JSONDecodeError:  # Changed from bare except
            data = {}

        # Extract parameters from the request body
        coin = data.get("coin")
        resolution = data.get("resolution")
        start_time = data.get("startTime")
        end_time = data.get("endTime")
        limit = data.get("limit")

        if coin and resolution:
            # Convert coin to standardized trading pair
            trading_pair = f"{coin}-USDT"

            # Convert exchange interval format to standardized format
            interval = next(
                (k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == resolution), resolution
            )

            # Map HyperLiquid parameters to generic parameters expected by handle_klines
            return {
                "symbol": trading_pair,
                "interval": interval,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
            }

        return {}

    async def handle_instruments(self, server, request):
        """
        Handle the HyperLiquid instruments endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with exchange information.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": "Rate limit exceeded"}, status=429)

        instruments = []
        for trading_pair in server.trading_pairs:
            base, quote = trading_pair.split("-", 1)
            instruments.append(
                {
                    "coin": base,
                    "baseCurrency": base,
                    "quoteCurrency": quote,
                    "type": "spot" if self.exchange_type.name.endswith("SPOT") else "perpetual",
                    "status": "ONLINE",
                    "tickSize": "0.01",
                    "stepSize": "0.001",
                    "minQty": "0.001",
                    "maxQty": "10000.0",
                }
            )

        return web.json_response(instruments)

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
