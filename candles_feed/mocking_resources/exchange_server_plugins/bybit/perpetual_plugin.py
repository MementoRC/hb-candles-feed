"""
Bybit Perpetual plugin implementation for the mock exchange server.
"""
from candles_feed.adapters.bybit.constants import PERPETUAL_WSS_URL
from candles_feed.adapters.bybit.perpetual_adapter import BybitPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType

from .base_plugin import BybitBasePlugin


class BybitPerpetualPlugin(BybitBasePlugin):
    """
    Bybit Perpetual plugin for the mock exchange server.

    This plugin implements the Bybit Perpetual API for the mock server,
    translating between the standardized mock server format and the
    Bybit-specific formats.
    """

    def __init__(self):
        """
        Initialize the Bybit Perpetual plugin.
        """
        super().__init__(ExchangeType.BYBIT_PERPETUAL, BybitPerpetualAdapter)

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Bybit Perpetual.

        :returns: The base WebSocket API URL.
        """
        return PERPETUAL_WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Bybit Perpetual.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/v5/market/kline": ("GET", "handle_klines"),
            "/v5/market/time": ("GET", "handle_time"),
            "/v5/market/instruments-info": ("GET", "handle_instruments"),
        }

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as a Bybit Perpetual REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from Bybit's REST API.
        """
        response = super().format_rest_candles(candles, trading_pair, interval)
        response["result"]["category"] = "linear"
        return response
