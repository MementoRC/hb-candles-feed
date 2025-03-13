"""
Hyperliquid Perpetual plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.hyperliquid.constants import PERP_WSS_URL
from candles_feed.adapters.hyperliquid.perpetual_adapter import HyperliquidPerpetualAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.hyperliquid.base_plugin import HyperliquidBasePlugin


class HyperliquidPerpetualPlugin(HyperliquidBasePlugin):
    """
    Hyperliquid Perpetual plugin for the mock exchange server.

    This plugin implements the Hyperliquid Perpetual API for the mock server,
    translating between the standardized mock server format and the
    Hyperliquid-specific formats.
    """

    def __init__(self):
        """
        Initialize the Hyperliquid Perpetual plugin.
        """
        super().__init__(ExchangeType.HYPERLIQUID_PERPETUAL, HyperliquidPerpetualAdapter)

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Hyperliquid Perpetual.

        :returns: The base WebSocket API URL.
        """
        return PERP_WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Hyperliquid Perpetual.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/info": ("POST", "handle_klines"),
            "/meta": ("POST", "handle_instruments"),
        }