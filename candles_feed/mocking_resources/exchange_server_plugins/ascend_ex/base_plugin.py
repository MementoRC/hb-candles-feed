"""
Base plugin for AscendEx exchange plugins.
"""

from abc import ABC
from typing import Any
from aiohttp import web

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.ascend_ex.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    SPOT_REST_URL,
    SPOT_WSS_URL
)
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class AscendExBasePlugin(ExchangePlugin, ABC):
    """
    Base class for AscendEx exchange plugins.

    This class provides shared functionality for AscendEx spot plugins.
    """

    def __init__(self, exchange_type: ExchangeType, adapter_class: type[BaseAdapter]):
        """
        Initialize the AscendEx base plugin.

        :param exchange_type: The exchange type.
        """
        super().__init__(exchange_type, adapter_class)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for AscendEx.

        :returns: The base REST API URL.
        """
        return f"{SPOT_REST_URL}"

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for AscendEx.

        :returns: The base WebSocket API URL.
        """
        return f"{SPOT_WSS_URL}"

    @property
    def ws_routes(self) -> dict[str, str]:
        """
        Get the WebSocket routes for AscendEx.

        :returns: A dictionary mapping URL paths to handler names.
        """
        return {"/api/pro/v1/websocket-for-hummingbot-liq-mining/stream": "handle_websocket"}

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as an AscendEx REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from AscendEx's REST API.
        """
        # Format according to AscendEx API:
        # {
        #   "code": 0,
        #   "data": [
        #     {
        #       "m": "bar",
        #       "s": "BTC/USDT",
        #       "data": {
        #         "ts": 1620000000000,
        #         "o": "50000",
        #         "h": "51000",
        #         "l": "49000",
        #         "c": "50500",
        #         "v": "525000"
        #       }
        #     }
        #   ]
        # }
        
        exchange_symbol = trading_pair.replace("-", "/")
        exchange_interval = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        
        formatted_candles = []
        for c in candles:
            formatted_candles.append({
                "m": "bar",
                "s": exchange_symbol,
                "data": {
                    "ts": int(c.timestamp_ms),
                    "o": str(c.open),
                    "h": str(c.high),
                    "l": str(c.low),
                    "c": str(c.close),
                    "v": str(c.quote_asset_volume)
                }
            })
        
        return {
            "code": 0,
            "data": formatted_candles
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as an AscendEx WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from AscendEx's WebSocket API.
        """
        # Format according to AscendEx WebSocket API:
        # {
        #   "m": "bar",
        #   "s": "BTC/USDT",
        #   "data": {
        #     "ts": 1620000000000,
        #     "o": "50000",
        #     "h": "51000",
        #     "l": "49000",
        #     "c": "50500",
        #     "v": "525000"
        #   }
        # }
        
        exchange_symbol = trading_pair.replace("-", "/")
        
        return {
            "m": "bar",
            "s": exchange_symbol,
            "data": {
                "ts": int(candle.timestamp_ms),
                "o": str(candle.open),
                "h": str(candle.high),
                "l": str(candle.low),
                "c": str(candle.close),
                "v": str(candle.quote_asset_volume)
            }
        }

    def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
        """
        Parse an AscendEx WebSocket subscription message.

        :param message: The subscription message from the client.
        :returns: A list of (trading_pair, interval) tuples that the client wants to subscribe to.
        """
        subscriptions = []
        
        # AscendEx uses an op and ch format:
        # {
        #   "op": "sub",
        #   "ch": "bar:1:BTC/USDT"
        # }
        
        if message.get("op") == "sub" and "ch" in message:
            ch = message["ch"]
            if ch.startswith("bar:"):
                parts = ch.split(":")
                if len(parts) >= 3:
                    interval = parts[1]
                    symbol = parts[2]
                    
                    # Convert exchange interval to standard interval
                    for std_interval, exchange_interval in INTERVAL_TO_EXCHANGE_FORMAT.items():
                        if exchange_interval == interval:
                            interval = std_interval
                            break
                    
                    # Convert symbol to standardized format (e.g., BTC-USDT)
                    symbol = symbol.replace("/", "-")
                    
                    subscriptions.append((symbol, interval))
                    
        return subscriptions

    def create_ws_subscription_success(
        self, message: dict, subscriptions: list[tuple[str, str]]
    ) -> dict:
        """
        Create an AscendEx WebSocket subscription success response.

        :param message: The original subscription message.
        :param subscriptions: List of (trading_pair, interval) tuples that were subscribed to.
        :returns: A subscription success response message.
        """
        # AscendEx returns a generic subscription success response
        return {
            "m": "sub",
            "id": message.get("id", ""),
            "code": 0
        }

    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.

        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: A string key used to track subscriptions.
        """
        # Format according to AscendEx subscription format: "bar:1:BTC/USDT"
        exchange_symbol = trading_pair.replace("-", "/")
        exchange_interval = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return f"bar:{exchange_interval}:{exchange_symbol}"

    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for AscendEx candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query
        
        # Get all AscendEx parameters
        symbol = params.get("symbol")
        interval = params.get("interval")
        n = params.get("n")
        to = params.get("to")
        
        if symbol:
            # Convert symbol from AscendEx format (BTC/USDT) to standard format (BTC-USDT)
            symbol = symbol.replace("/", "-")
        
        if interval:
            # Convert interval from AscendEx format to standard format
            for std_interval, exchange_interval in INTERVAL_TO_EXCHANGE_FORMAT.items():
                if exchange_interval == interval:
                    interval = std_interval
                    break
        
        if n is not None:
            try:
                n = int(n)
                if n > 500:  # AscendEx limit is 500
                    n = 500
            except ValueError:
                n = 500  # Default limit
                    
        # Map AscendEx parameters to generic parameters expected by handle_klines
        return {
            "symbol": symbol,            
            "interval": interval,        
            "end_time": to,         
            "limit": n,              
            
            # Also keep the original parameter names for reference
            "to": to,
            "n": n,
        }

    async def handle_instruments(self, server, request):
        """
        Handle the AscendEx instruments endpoint.

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
            instruments.append({
                "symbol": trading_pair.replace("-", "/"),
                "baseAsset": base,
                "quoteAsset": quote,
                "status": "Normal",
                "minQty": "0.0001",
                "maxQty": "100000",
                "minNotional": "5",
                "maxNotional": "1000000",
                "tickSize": "0.01",
                "lotSize": "0.0001"
            })

        return web.json_response({"code": 0, "data": instruments})
