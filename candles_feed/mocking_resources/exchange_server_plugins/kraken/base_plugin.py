"""
Base class for Kraken exchange plugins.

This class provides shared functionality for Kraken plugins.
"""

import contextlib
from abc import ABC
from typing import Any, Union

from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.kraken.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class KrakenBasePlugin(ExchangePlugin, ABC):
    """
    Base class for Kraken exchange plugins.

    This class provides shared functionality for Kraken exchange plugins.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the Kraken base plugin.

        :param exchange_type: The exchange type.
        :param adapter_class: The adapter class for this exchange.
        """
        super().__init__(exchange_type, adapter_class)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Kraken.

        :returns: The base REST API URL.
        """
        return f"{SPOT_REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Kraken.

        :returns: The base WebSocket API URL.
        """
        return f"{SPOT_WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Kraken.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/ws": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as a Kraken REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from Kraken's REST API.
        """
        # Format according to Kraken REST API candle response:
        # {
        #   "error": [],
        #   "result": {
        #     "XXBTZUSD": [
        #       [
        #         1616662800,     // Time
        #         "52556.5",      // Open
        #         "52650.0",      // High
        #         "52450.0",      // Low
        #         "52483.4",      // Close
        #         "52519.9",      // VWAP
        #         "56.72067891",  // Volume
        #         158             // Count
        #       ],
        #       ...
        #     ],
        #     "last": 1616691600
        #   }
        # }

        kraken_formatted_pair = self._format_trading_pair(trading_pair)
        formatted_candles = []

        for candle in candles:
            # Format each candle according to Kraken's format
            formatted_candle = [
                int(candle.timestamp),  # Time in seconds as integer
                str(candle.open),  # Open price as string
                str(candle.high),  # High price as string
                str(candle.low),  # Low price as string
                str(candle.close),  # Close price as string
                str(candle.close * 0.9999),  # VWAP - approximated as slightly less than close
                str(candle.volume),  # Volume as string
                100,  # Count (number of trades) - placeholder value
            ]
            formatted_candles.append(formatted_candle)

        return {
            "error": [],
            "result": {
                kraken_formatted_pair: formatted_candles,
                "last": int(candles[-1].timestamp) if candles else 0,
            },
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> Union[list, dict]:
        """
        Format candle data as a Kraken WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from Kraken's WebSocket API.
        """
        # Format according to Kraken WebSocket message:
        # [
        #   0,                    // ChannelID
        #   [
        #     "1542057314.748456", // Time
        #     "1542057360.435743", // End
        #     "3586.70000",       // Open
        #     "3586.70000",       // High
        #     "3586.60000",       // Low
        #     "3586.60000",       // Close
        #     "3586.68894",       // VWAP
        #     "0.03373000",       // Volume
        #     2                   // Count
        #   ],
        #   "ohlc-1",            // Channel name with interval
        #   "XBT/USD"            // Pair
        # ]

        interval_num = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, 1)
        kraken_formatted_pair = self._format_trading_pair(trading_pair)

        # Calculate end time (this would normally be calculated by Kraken)
        end_time = candle.timestamp + self._interval_to_seconds(interval)

        # Format the candle data
        candle_data = [
            f"{candle.timestamp}.000000",  # Time with microsecond precision
            f"{end_time}.000000",  # End time with microsecond precision
            f"{candle.open:.5f}",  # Open price with 5 decimals
            f"{candle.high:.5f}",  # High price with 5 decimals
            f"{candle.low:.5f}",  # Low price with 5 decimals
            f"{candle.close:.5f}",  # Close price with 5 decimals
            f"{candle.close * 0.9999:.5f}",  # VWAP approximated with 5 decimals
            f"{candle.volume:.8f}",  # Volume with 8 decimals
            100,  # Count - placeholder
        ]

        # Return the message as an array (Kraken uses arrays, not objects, for WebSocket messages)
        return [
            0,  # Channel ID (placeholder)
            candle_data,  # Candle data array
            f"ohlc-{interval_num}",  # Channel name with interval
            kraken_formatted_pair,  # Formatted trading pair
        ]

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Kraken WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        # Kraken subscription format:
        # {
        #   "name": "subscribe",
        #   "reqid": 1,
        #   "pair": ["XBT/USD"],
        #   "subscription": {
        #     "name": "ohlc",
        #     "interval": 1
        #   }
        # }

        subscriptions = []
        if isinstance(message, dict) and message.get("name") == "subscribe":
            subscription = message.get("subscription", {})

            if subscription.get("name") == "ohlc":
                interval_min = subscription.get("interval")
                # Convert interval in minutes to our standard format
                interval = next(
                    (k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == interval_min),
                    "1m",  # Default to 1m if not found
                )

                # Extract trading pairs
                for pair in message.get("pair", []):
                    # Convert Kraken pair (XBT/USD) to our standard format (BTC-USD)
                    trading_pair = self._reverse_format_trading_pair(pair)
                    subscriptions.append((trading_pair, interval))

        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create a Kraken WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        # Kraken subscription response format:
        # {
        #   "channelID": 42,
        #   "channelName": "ohlc-1",
        #   "pair": "XBT/USD",
        #   "reqid": 1,
        #   "status": "subscribed",
        #   "subscription": {
        #     "interval": 1,
        #     "name": "ohlc"
        #   }
        # }

        # For each subscription, create a response
        responses = []
        message.get("subscription", {})
        reqid = message.get("reqid", 1)

        # Create a response for each pair
        for trading_pair, interval in subscriptions:
            interval_num = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, 1)
            kraken_pair = self._format_trading_pair(trading_pair)

            responses.append(
                {
                    "channelID": hash(f"{kraken_pair}_{interval}")
                    % 1000,  # Generate a pseudo-random channel ID
                    "channelName": f"ohlc-{interval_num}",
                    "pair": kraken_pair,
                    "reqid": reqid,
                    "status": "subscribed",
                    "subscription": {"interval": interval_num, "name": "ohlc"},
                }
            )

        # Return the first response if there's only one
        # (Kraken sends separate messages for each subscription)
        return (
            responses[0]
            if responses
            else {"errorMessage": "No valid subscriptions found", "status": "error", "reqid": reqid}
        )

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        kraken_pair = self._format_trading_pair(trading_pair)
        interval_num = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, 1)
        return f"ohlc-{interval_num}_{kraken_pair}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for Kraken candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query

        # Kraken uses 'pair', 'interval' in minutes, and 'since' parameter
        pair = params.get("pair")
        interval_min = params.get("interval")
        since = params.get("since")

        # Convert Kraken's pair format to our standard format
        symbol = self._reverse_format_trading_pair(pair) if pair else None

        # Convert interval in minutes to our standard format
        interval = next(
            (k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if str(v) == interval_min),
            "1m",  # Default to 1m if not found
        )

        # Map Kraken parameters to generic parameters
        result = {
            "symbol": symbol,
            "interval": interval,
            "limit": 720,  # Kraken's default limit
        }

        # Handle since parameter (start time)
        if since:
            with contextlib.suppress(ValueError):
                result["start_time"] = int(since)

        return result

    async def handle_time(self, server, request):
        """
        Handle the Kraken time endpoint.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with server time.
        """
        await server._simulate_network_conditions()

        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "rest"):
            return web.json_response({"error": ["EAPI:Rate limit exceeded"]}, status=429)

        current_time = int(server._time())

        return web.json_response(
            {
                "error": [],
                "result": {
                    "unixtime": current_time,
                    "rfc1123": "Thu, 1 Jan 1970 00:00:00 +0000",  # Placeholder, not actually formatted
                },
            }
        )

    def _format_trading_pair(self, trading_pair: str) -> str:
        """
        Format trading pair to Kraken's format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT").
        :returns: Trading pair in Kraken format (e.g., "XBTUSD").
        """
        if not trading_pair or "-" not in trading_pair:
            return trading_pair

        base, quote = trading_pair.split("-")

        # Handle special cases
        if base == "BTC":
            base = "XBT"
        if quote == "USDT":
            quote = "USD"

        # For major currencies, Kraken adds X/Z prefix

        # Format as Kraken expects - for simplicity we'll use slash format
        # In a complete implementation, we'd check the context (REST vs WS)
        # REST API uses concatenated format like XXBTZUSD
        # WebSocket uses slash format like XBT/USD
        return f"{base}/{quote}"

    def _reverse_format_trading_pair(self, kraken_pair: str) -> str:
        """
        Convert Kraken's trading pair format back to our standard format.

        :param kraken_pair: Trading pair in Kraken format (e.g., "XXBTZUSD" or "XBT/USD").
        :returns: Trading pair in standard format (e.g., "BTC-USD").
        """
        if not kraken_pair:
            return kraken_pair

        # Handle slash format (WebSocket)
        if "/" in kraken_pair:
            base, quote = kraken_pair.split("/")

            # Handle special cases
            if base == "XBT":
                base = "BTC"
            if quote == "USD" and base == "BTC":
                quote = "USDT"

            return f"{base}-{quote}"

        # Handle concatenated format (REST)
        # This is complex due to Kraken's prefixing - simplified implementation
        if kraken_pair.startswith("X") and kraken_pair.endswith("ZUSD"):
            # Common case XXBTZUSD -> BTC-USDT
            base = kraken_pair[1:-4]
            if base == "XBT":
                base = "BTC"
            return f"{base}-USDT"

        # Fallback - just return as is with a hyphen
        if len(kraken_pair) >= 6:
            # Attempt simple split in the middle
            mid = len(kraken_pair) // 2
            return f"{kraken_pair[:mid]}-{kraken_pair[mid:]}"

        return kraken_pair

    def _interval_to_seconds(self, interval: str) -> int:
        """
        Convert interval string to seconds.

        :param interval: Interval string (e.g., "1m", "1h").
        :returns: Interval in seconds.
        """
        return INTERVALS.get(interval, 60)  # Default to 1m if not found
