"""
Binance spot exchange adapter for the Candle Feed framework.
"""

from typing import override

from candles_feed.adapters.adapter_mixins import TestnetSupportMixin
from candles_feed.adapters.binance.base_adapter import BinanceBaseAdapter
from candles_feed.adapters.binance.constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_TESTNET_REST_URL,
    SPOT_TESTNET_WSS_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_config import EndpointType, NetworkConfig
from candles_feed.core.rate_limiter import RestRateLimit


@ExchangeRegistry.register("binance_spot")
class BinanceSpotAdapter(TestnetSupportMixin, BinanceBaseAdapter):
    """Binance spot exchange adapter with testnet support."""

    # hummingbot/data_feed/candles_feed/binance_spot_candles/constants.py:35-36 — klines own limit 1200/60s (weight 1) is stricter than the 6000 weight/60s pool
    # Own pool: api.binance.com has an IP budget separate from fapi.binance.com (binance_perpetual).
    REST_RATE_LIMIT = RestRateLimit(max_requests=1200, period_seconds=60)
    # hummingbot/data_feed/candles_feed/binance_spot_candles/constants.py:36 links klines to REQUEST_WEIGHT at weight 1 (pool also in connector/exchange/binance/binance_constants.py:42)
    # Real klines weight grows with the request limit; weight 1 is what the upstream candles constants use.
    REST_HOST_RATE_LIMIT_ID = "REQUEST_WEIGHT"
    REST_HOST_RATE_LIMIT_WEIGHT = 1

    def __init__(self, *args, network_config: NetworkConfig | None = None, **kwargs):
        """Initialize the adapter.

        :param network_config: Network configuration for testnet/production
        :param args: Additional positional arguments
        :param kwargs: Additional keyword arguments
        """
        super().__init__(*args, network_config=network_config, **kwargs)  # type: ignore

    @override
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles.

        This method implements TestnetSupportMixin's URL selection logic
        to choose between production and testnet URLs.

        :return: REST API URL
        """
        # Use TestnetSupportMixin's implementation which checks network_config
        if hasattr(self, "network_config") and hasattr(self, "_bypass_network_selection"):
            if getattr(self, "_bypass_network_selection", False):
                return self._get_production_rest_url()
            elif self.network_config and self.network_config.is_testnet_for(EndpointType.CANDLES):
                return self._get_testnet_rest_url()

        # Default to production URL
        return self._get_production_rest_url()

    @override
    def _get_ws_url(self) -> str:
        """Get WebSocket URL.

        This method implements TestnetSupportMixin's URL selection logic
        to choose between production and testnet URLs.

        :return: WebSocket URL
        """
        # Logic from TestnetSupportMixin's _get_ws_url
        if getattr(self, "_bypass_network_selection", False):
            return self._get_production_ws_url()
        elif self.network_config and self.network_config.is_testnet_for(EndpointType.CANDLES):
            return self._get_testnet_ws_url()
        return self._get_production_ws_url()

    @override
    def _get_production_rest_url(self) -> str:
        """Get production REST URL for candles.

        :return: Production REST URL for candles endpoint
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @override
    def _get_production_ws_url(self) -> str:
        """Get production WebSocket URL.

        :return: Production WebSocket URL
        """
        return SPOT_WSS_URL

    @override
    def _get_testnet_rest_url(self) -> str:
        """Get testnet REST URL for candles.

        :return: Testnet REST URL for candles endpoint
        """
        return f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @override
    def _get_testnet_ws_url(self) -> str:
        """Get testnet WebSocket URL.

        :return: Testnet WebSocket URL
        """
        return SPOT_TESTNET_WSS_URL
