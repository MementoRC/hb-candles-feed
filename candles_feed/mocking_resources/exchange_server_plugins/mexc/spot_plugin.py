"""
MEXC Spot plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.mexc.spot_adapter import MEXCSpotAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.mexc.base_plugin import MEXCBasePlugin
from candles_feed.adapters.mexc.constants import SPOT_WSS_URL


class MEXCSpotPlugin(MEXCBasePlugin):
    """
    MEXC Spot plugin for the mock exchange server.

    This plugin implements the MEXC Spot API for the mock server,
    translating between the standardized mock server format and the
    MEXC-specific formats.
    """

    def __init__(self):
        """
        Initialize the MEXC Spot plugin.
        """
        super().__init__(ExchangeType.MEXC_SPOT, MEXCSpotAdapter)

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for MEXC Spot.

        :returns: The base WebSocket API URL.
        """
        return SPOT_WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for MEXC Spot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/v3/ping": ("GET", "handle_ping"),
            "/api/v3/time": ("GET", "handle_time"),
            "/api/v3/klines": ("GET", "handle_klines"),
            "/api/v3/exchangeInfo": ("GET", "handle_exchange_info"),
        }