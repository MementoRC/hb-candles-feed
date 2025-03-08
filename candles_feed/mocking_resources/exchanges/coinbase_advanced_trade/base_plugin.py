"""
Base class for Coinbase Advanced Trade exchange plugins.

This class provides shared functionality for Coinbase Advanced Trade plugins.
"""

import json
from abc import ABC
from datetime import datetime, timezone
from typing import Any
from aiohttp import web
from candles_feed.adapters.base_adapter import BaseAdapter

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.adapters.coinbase_advanced_trade.constants import (
    INTERVALS,
    INTERVAL_TO_EXCHANGE_FORMAT,
    REST_URL,
    WSS_URL,
)


class CoinbaseAdvancedTradeBasePlugin(ExchangePlugin, ABC):
    """
    Base class for Coinbase Advanced Trade exchange plugins.

    This class provides shared functionality for Coinbase Advanced Trade plugins.
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
        return f"{REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Coinbase Advanced Trade.

        :returns: The base WebSocket API URL.
        """
        return f"{WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for Coinbase Advanced Trade.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as a Coinbase Advanced Trade REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from Coinbase Advanced Trade's REST API.
        """
        # Format according to Coinbase REST API candle response:
        # {
        #   "candles": [
        #     {
        #       "start": "2022-05-15T16:00:00Z",
        #       "low": "29288.38",
        #       "high": "29477.29",
        #       "open": "29405.34",
        #       "close": "29374.47",
        #       "volume": "142.0450069"
        #     },
        #     ...
        #   ]
        # }
        
        formatted_candles = []
        for candle in candles:
            timestamp_iso = datetime.fromtimestamp(candle.timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            formatted_candles.append({
                "start": timestamp_iso,
                "low": str(candle.low),
                "high": str(candle.high),
                "open": str(candle.open),
                "close": str(candle.close),
                "volume": str(candle.volume)
            })
            
        return {
            "candles": formatted_candles
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
        #   "client_id": "...",
        #   "timestamp": "2023-02-14T17:02:36.346Z",
        #   "sequence_num": 1234,
        #   "events": [
        #     {
        #       "type": "candle",
        #       "candles": [
        #         {
        #           "start": "2023-02-14T17:01:00Z",
        #           "low": "22537.4",
        #           "high": "22540.7",
        #           "open": "22537.4",
        #           "close": "22540.7",
        #           "volume": "0.1360142"
        #         }
        #       ]
        #     }
        #   ]
        # }
        
        timestamp_iso = datetime.fromtimestamp(candle.timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        current_time_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3]
        
        return {
            "channel": "candles",
            "client_id": "mock-client",
            "timestamp": current_time_iso,
            "sequence_num": int(candle.timestamp * 1000) % 100000,
            "events": [
                {
                    "type": "candle",
                    "candles": [
                        {
                            "start": timestamp_iso,
                            "low": str(candle.low),
                            "high": str(candle.high),
                            "open": str(candle.open),
                            "close": str(candle.close),
                            "volume": str(candle.volume)
                        }
                    ]
                }
            ]
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse a Coinbase Advanced Trade WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        # Coinbase subscription format:
        # {
        #   "type": "subscribe",
        #   "product_ids": ["BTC-USD"],
        #   "channel": "candles",
        #   "granularity": 60
        # }
        
        subscriptions = []
        if isinstance(message, dict) and message.get("type") == "subscribe" and message.get("channel") == "candles":
            granularity = message.get("granularity")
            if granularity is not None:
                # Convert granularity (seconds) to interval format
                interval = next(
                    (k for k, v in INTERVALS.items() if v == granularity), 
                    f"{granularity}s"  # Fallback if not found
                )
                
                for product_id in message.get("product_ids", []):
                    subscriptions.append((product_id, interval))
                    
        return subscriptions

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
        #   "type": "subscriptions",
        #   "channels": [
        #     {
        #       "name": "candles",
        #       "product_ids": ["BTC-USD"]
        #     }
        #   ]
        # }
        
        return {
            "type": "subscriptions",
            "channels": [
                {
                    "name": "candles",
                    "product_ids": [tp for tp, _ in subscriptions]
                }
            ]
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        # Format matching Coinbase's subscription parameters
        granularity = INTERVALS.get(interval, 60)  # Default to 1m (60 seconds)
        return f"candles_{trading_pair}_{granularity}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for Coinbase Advanced Trade candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query
        
        # In Coinbase the product_id is in the URL path, extract it from the request's url
        product_id = request.path.rsplit('/', 2)[-2] if '/products/' in request.path else None
        
        # Convert Coinbase-specific parameter names to generic ones
        granularity = params.get("granularity")
        start = params.get("start")
        end = params.get("end")
        
        # Convert granularity to interval format
        interval = next(
            (k for k, v in INTERVALS.items() if str(v) == granularity),
            "1m"  # Default to 1m if not found
        )
        
        # Map Coinbase parameters to generic parameters
        result = {
            "symbol": product_id,
            "interval": interval,
            "limit": 300,  # Coinbase maximum
        }
        
        # Handle ISO timestamps
        if start:
            try:
                # Try to parse ISO format first
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                result["start_time"] = int(dt.timestamp())
            except ValueError:
                # If not ISO, assume it's already a timestamp
                result["start_time"] = start
                
        if end:
            try:
                dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                result["end_time"] = int(dt.timestamp())
            except ValueError:
                result["end_time"] = end
        
        return result

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
            base, quote = trading_pair.split("-", 1)
            products.append({
                "product_id": trading_pair,
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
                "trading_disabled": False
            })
            
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
            
        current_time = datetime.fromtimestamp(server._time(), tz=timezone.utc)
        iso_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3]
        
        return web.json_response({
            "iso": iso_time,
            "epoch": server._time()
        })