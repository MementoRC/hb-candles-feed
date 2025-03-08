"""
OKX spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.okx.base_adapter import OKXBaseAdapter
from candles_feed.adapters.okx.constants import (
    SPOT_REST_URL,
    SPOT_CANDLES_ENDPOINT,
    SPOT_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("okx_spot")
class OKXSpotAdapter(OKXBaseAdapter):
    """OKX spot exchange adapter."""

    @staticmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return SPOT_WSS_URL
