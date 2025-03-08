"""
Gate.io perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.gate_io.constants import (
    PERP_CANDLES_ENDPOINT,
    PERP_CHANNEL_NAME,
    PERP_WSS_URL,
    REST_URL,
)
from candles_feed.adapters.gate_io.base_adapter import GateIoBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("gate_io_perpetual")
class GateIoPerpetualAdapter(GateIoBaseAdapter):
    """Gate.io perpetual exchange adapter."""

    @staticmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return f"{REST_URL}{PERP_CANDLES_ENDPOINT}"

    @staticmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return PERP_WSS_URL

    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :return: Channel name string
        """
        return PERP_CHANNEL_NAME
