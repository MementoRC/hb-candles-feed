"""
Gate.io spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.gate_io.constants import (
    SPOT_CHANNEL_NAME,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.adapters.gate_io.gate_io_base_adapter import GateIoBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("gate_io_spot")
class GateIoSpotAdapter(GateIoBaseAdapter):
    """Gate.io spot exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return SPOT_REST_URL

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return SPOT_WSS_URL

    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :return: Channel name string
        """
        return SPOT_CHANNEL_NAME