"""
Bybit perpetual exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.adapters.bybit.base_adapter import BybitBaseAdapter
from candles_feed.adapters.bybit.constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("bybit_perpetual")
class BybitPerpetualAdapter(BybitBaseAdapter):
    """Bybit perpetual exchange adapter."""

    # hummingbot/data_feed/candles_feed/bybit_perpetual_candles/constants.py:38 links candles to GETLimit at weight 1 (pool also in connector/derivative/bybit_perpetual/bybit_perpetual_constants.py:114)
    # Pool ids differ between spot and perpetual, so each variant declares its own.
    REST_HOST_RATE_LIMIT_ID = "GETLimit"
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
    def get_category_param(self) -> str:
        """Get the category parameter for the market type.

        :returns: Category parameter string
        """
        return "linear"
