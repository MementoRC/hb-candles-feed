"""
Gate.io spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.gate_io.constants import (
    REST_URL,
    SPOT_CANDLES_ENDPOINT,
    SPOT_CHANNEL_NAME,
    SPOT_WSS_URL,
)
from candles_feed.adapters.gate_io.base_adapter import GateIoBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("gate_io_spot")
class GateIoSpotAdapter(GateIoBaseAdapter):
    """Gate.io spot exchange adapter."""

    @staticmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return f"{REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return SPOT_WSS_URL

    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :return: Channel name string
        """
        return SPOT_CHANNEL_NAME