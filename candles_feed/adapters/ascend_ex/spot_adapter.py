"""
AscendEx spot exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.ascend_ex.base_adapter import AscendExBaseAdapter
from candles_feed.adapters.ascend_ex.constants import (
    CANDLES_ENDPOINT,
    REST_URL,
    WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("ascend_ex_spot")
class AscendExSpotAdapter(AscendExBaseAdapter):
    """AscendEx spot exchange adapter."""

    @staticmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    @staticmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.

       :returns: WebSocket URL.
        """
        return WSS_URL
