"""
Gate.io perpetual exchange adapter for the Candle Feed framework.
"""

from .constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_CHANNEL_NAME,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from .base_adapter import GateIoBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("gate_io_perpetual")
class GateIoPerpetualAdapter(GateIoBaseAdapter):
    """Gate.io perpetual exchange adapter."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return PERPETUAL_WSS_URL

    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :returns: Channel name string
        """
        return PERPETUAL_CHANNEL_NAME
