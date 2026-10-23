"""
Gate.io spot exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.rate_limiter import RestRateLimit

from .base_adapter import GateIoBaseAdapter
from .constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_CHANNEL_NAME,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)


@ExchangeRegistry.register("gate_io_spot")
class GateIoSpotAdapter(GateIoBaseAdapter):
    """Gate.io spot exchange adapter."""

    # hummingbot/data_feed/candles_feed/gate_io_spot_candles/constants.py:31,34,37 — public points pool 200/2s, candles linked weight 1
    REST_RATE_LIMIT = RestRateLimit(max_requests=200, period_seconds=2)

    @staticmethod
    @override
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    @override
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return SPOT_WSS_URL

    @override
    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :returns: Channel name string
        """
        return SPOT_CHANNEL_NAME
