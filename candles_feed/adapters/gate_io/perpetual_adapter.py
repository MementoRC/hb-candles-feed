"""
Gate.io perpetual exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.rate_limiter import RestRateLimit

from .base_adapter import GateIoBaseAdapter
from .constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_CHANNEL_NAME,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)


@ExchangeRegistry.register("gate_io_perpetual")
class GateIoPerpetualAdapter(GateIoBaseAdapter):
    """Gate.io perpetual exchange adapter."""

    # hummingbot/data_feed/candles_feed/gate_io_perpetual_candles/constants.py:31,40,42 — public points pool 300/1s, candles linked weight 1
    REST_RATE_LIMIT = RestRateLimit(max_requests=300, period_seconds=1)
    # hummingbot/data_feed/candles_feed/gate_io_perpetual_candles/constants.py:42 links candles to PublicPoints (default weight 1) (pool also in connector/derivative/gate_io_perpetual/gate_io_perpetual_constants.py:61)
    REST_HOST_RATE_LIMIT_ID = "PublicPoints"
    REST_HOST_RATE_LIMIT_WEIGHT = 1

    @staticmethod
    @override
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"

    @staticmethod
    @override
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return PERPETUAL_WSS_URL

    @override
    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :returns: Channel name string
        """
        return PERPETUAL_CHANNEL_NAME
