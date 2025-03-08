"""
Binance Perpetual plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.binance.constants import PERPETUAL_REST_URL, PERPETUAL_WSS_URL
from candles_feed.adapters.binance.perpetual_adapter import BinancePerpetualAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchanges.binance.base_plugin import BinanceBasePlugin


class BinancePerpetualPlugin(BinanceBasePlugin):
    """
    Binance Perpetual plugin for the mock exchange server.

    This plugin implements the Binance Perpetual API for the mock server,
    translating between the standardized mock server format and the
    Binance-specific formats.
    """

    def __init__(self):
        """
        Initialize the Binance Perpetual plugin.
        """
        super().__init__(ExchangeType.BINANCE_PERPETUAL, BinancePerpetualAdapter)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for Binance Perpetual.

        :returns: The base REST API URL.
        """
        return PERPETUAL_REST_URL

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Binance Perpetual.

        :returns: The base WebSocket API URL.
        """
        return PERPETUAL_WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Binance Perpetual.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/fapi/v1/klines": ("GET", "handle_klines"),
            "/fapi/v1/time": ("GET", "handle_time"),
            "/fapi/v1/exchangeInfo": ("GET", "handle_exchange_info"),
        }