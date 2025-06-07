"""
Hyperliquid Spot plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.hyperliquid.constants import SPOT_WSS_URL
from candles_feed.adapters.hyperliquid.spot_adapter import HyperliquidSpotAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.hyperliquid.base_plugin import (
    HyperliquidBasePlugin,
)


class HyperliquidSpotPlugin(HyperliquidBasePlugin):
    """
    Hyperliquid Spot plugin for the mock exchange server.

    This plugin implements the Hyperliquid Spot API for the mock server,
    translating between the standardized mock server format and the
    Hyperliquid-specific formats.
    """

    def __init__(self):
        """
        Initialize the Hyperliquid Spot plugin.
        """
        super().__init__(ExchangeType.HYPERLIQUID_SPOT, HyperliquidSpotAdapter)

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for Hyperliquid Spot.

        :returns: The base WebSocket API URL.
        """
        return SPOT_WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Hyperliquid Spot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/info": ("POST", "handle_klines"),
            "/meta": ("POST", "handle_instruments"),
        }
