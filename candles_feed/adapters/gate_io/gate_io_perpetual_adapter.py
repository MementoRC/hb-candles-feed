"""
Gate.io perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.gate_io.constants import (
    PERP_CHANNEL_NAME,
    PERP_REST_URL,
    PERP_WSS_URL,
)
from candles_feed.adapters.gate_io.gate_io_base_adapter import GateIoBaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("gate_io_perpetual")
class GateIoPerpetualAdapter(GateIoBaseAdapter):
    """Gate.io perpetual exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return PERP_REST_URL

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return PERP_WSS_URL

    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :return: Channel name string
        """
        return PERP_CHANNEL_NAME