"""
Binance Spot plugin implementation for the mock exchange server.
"""

from aiohttp import web

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType

from .base_plugin import BinanceBasePlugin


class BinanceSpotPlugin(BinanceBasePlugin):
    """
    Binance Spot plugin for the mock exchange server.

    This plugin implements the Binance Spot API for the mock server,
    translating between the standardized mock server format and the
    Binance-specific formats.
    """

    def __init__(self):
        """
        Initialize the Binance Spot plugin.
        """
        super().__init__(ExchangeType.BINANCE_SPOT, BinanceSpotAdapter)

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Binance Spot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            # Include handlers for candles functionality
            "/api/v3/klines": ("GET", "handle_klines"),
            # Include general utility endpoints
            "/api/v3/ping": ("GET", "handle_ping"),
            "/api/v3/time": ("GET", "handle_time"),
            "/api/v3/exchangeInfo": ("GET", "handle_exchange_info"),
            # Include market data endpoints that might be useful for candles context
            "/api/v3/ticker/price": ("GET", "handle_ticker_price"),
        }

    async def handle_ui_klines(self, server, request):
        """
        Handle the Binance UI Klines endpoint.

        UI Klines return modified kline data, optimized for presentation of candlestick charts.
        The endpoint works exactly like the regular klines endpoint, with the same parameters
        and response format.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: A JSON response with candle data.
        """
        # UI Klines has the same implementation as regular klines for the mock server
        return await self.handle_klines(server, request)

    def parse_rest_candles_params(self, request: web.Request) -> dict:
        """
        Parse REST API parameters for Binance candle requests.

        Extended to support all Binance klines parameters:
        - symbol: Trading pair (required)
        - interval: Candle interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
        - startTime: Start time in milliseconds
        - endTime: End time in milliseconds
        - timeZone: Time zone adjustment (-12:00 to +14:00)
        - limit: Number of candles to return (default 500, max 1000)

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query

        # Get all Binance klines parameters
        symbol = params.get("symbol")
        interval = params.get("interval")
        start_time = params.get("startTime")
        end_time = params.get("endTime")
        time_zone = params.get("timeZone", "0")
        limit = params.get("limit")

        if limit is not None:
            try:
                limit = int(limit)
                limit = min(limit, 1000)
            except ValueError:
                limit = 500  # Default limit

        try:
            if ":" in time_zone:
                hours, minutes = time_zone.split(":")
                timezone_offset_hours = int(hours) + (int(minutes) / 60)
            else:
                timezone_offset_hours = int(time_zone)
        except (ValueError, TypeError):
            timezone_offset_hours = 0

        # Map Binance parameters to generic parameters expected by handle_klines
        return {
            "symbol": symbol,  # 'symbol' is the same in both
            "interval": interval,  # 'interval' is the same in both
            "start_time": start_time,  # 'startTime' in Binance maps to 'start_time' in generic handler
            "end_time": end_time,  # 'endTime' in Binance maps to 'end_time' in generic handler
            "time_zone": time_zone,  # 'timeZone' in Binance maps to 'time_zone'
            "limit": limit,  # 'limit' has the same name
            # Also keep the original Binance parameter names for reference
            "startTime": start_time,
            "endTime": end_time,
            "timeZone": time_zone,
            "timezone_offset_hours": timezone_offset_hours,
        }
