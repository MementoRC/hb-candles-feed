"""
Binance Spot plugin implementation for the mock exchange server.
"""

from typing import Any, Optional

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
        symbol: Optional[str] = params.get("symbol")
        interval: Optional[str] = params.get("interval")
        start_time_str: Optional[str] = params.get("startTime")
        end_time_str: Optional[str] = params.get("endTime")
        time_zone_str: str = params.get("timeZone", "0")  # Default to "0" if not provided
        limit_str: Optional[str] = params.get("limit")

        parsed_limit: int = 500  # Default limit
        if limit_str is not None:
            try:
                parsed_limit = int(limit_str)
                parsed_limit = min(parsed_limit, 1000)  # Max limit is 1000
            except ValueError:
                # If limit is not a valid integer, Binance might use default or error.
                # Here, we'll stick to a default or previously parsed valid value.
                # For simplicity, if invalid, it remains 500 or the last valid parsed_limit.
                pass  # Keep default if invalid string

        timezone_offset_hours: float = 0.0
        try:
            if ":" in time_zone_str:
                hours, minutes = time_zone_str.split(":")
                timezone_offset_hours = float(hours) + (float(minutes) / 60.0)
            else:
                timezone_offset_hours = float(time_zone_str)
        except (ValueError, TypeError):
            timezone_offset_hours = 0.0  # Default to 0 if parsing fails

        # Map Binance parameters to generic parameters expected by handle_klines
        # Ensure types are consistent where possible (e.g. start_time, end_time as str as received)
        return_params: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
            "start_time": start_time_str,  # Pass as string, server.py handle_klines will parse
            "end_time": end_time_str,  # Pass as string
            "time_zone": time_zone_str,
            "limit": parsed_limit,
            # Also keep the original Binance parameter names for reference if needed by plugin
            "startTime": start_time_str,
            "endTime": end_time_str,
            "timeZone": time_zone_str,
            "timezone_offset_hours": timezone_offset_hours,  # This is calculated for internal use
        }
        return return_params
