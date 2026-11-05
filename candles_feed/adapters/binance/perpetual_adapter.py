"""
Binance perpetual exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.adapters.binance.base_adapter import BinanceBaseAdapter
from candles_feed.adapters.binance.constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.rate_limiter import RestRateLimit


@ExchangeRegistry.register("binance_perpetual")
class BinancePerpetualAdapter(BinanceBaseAdapter):
    """Binance perpetual exchange adapter."""

    # hummingbot/data_feed/candles_feed/binance_perpetual_candles/constants.py:35-41 — klines own limit 1200/60s at weight 2 -> 600 req/60s (pool 1200 weight/60s, linked weight 1, is looser)
    # Own pool: fapi.binance.com has an IP budget separate from api.binance.com (binance_spot).
    REST_RATE_LIMIT = RestRateLimit(max_requests=600, period_seconds=60)
    # hummingbot/data_feed/candles_feed/binance_perpetual_candles/constants.py:41 links klines to REQUEST_WEIGHT at weight 1 (pool also in connector/derivative/binance_perpetual/binance_perpetual_constants.py:75)
    # Real klines weight grows with the request limit; weight 1 is what the upstream candles constants use.
    REST_HOST_RATE_LIMIT_ID = "REQUEST_WEIGHT"
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
