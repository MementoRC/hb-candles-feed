"""
AscendEx spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import AscendExBaseAdapter
from .constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)


@ExchangeRegistry.register("ascend_ex_spot")
class AscendExSpotAdapter(AscendExBaseAdapter):
    """AscendEx spot exchange adapter."""

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL.
        """
        return SPOT_WSS_URL
