"""
Binance spot exchange adapter for the Candle Feed framework.
"""

from typing import Optional

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


@ExchangeRegistry.register("binance_spot")
class BinanceSpotAdapter(BinanceBaseAdapter, TestnetSupportMixin):
    """Binance spot exchange adapter with testnet support."""

    def __init__(self, *args, network_config: Optional[NetworkConfig] = None, **kwargs):
        """Initialize the adapter.

        :param network_config: Network configuration for testnet/production
        :param args: Additional positional arguments
        :param kwargs: Additional keyword arguments
        """
        super().__init__(*args, network_config=network_config, **kwargs)  # type: ignore

    def _get_rest_url(self) -> str:  # type: ignore[override]
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

    def _get_ws_url(self) -> str:  # type: ignore[override]
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

    def _get_production_rest_url(self) -> str:  # type: ignore[override]
        """Get production REST URL for candles.

        :return: Production REST URL for candles endpoint
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def _get_production_ws_url(self) -> str:  # type: ignore[override]
        """Get production WebSocket URL.

        :return: Production WebSocket URL
        """
        return SPOT_WSS_URL

    def _get_testnet_rest_url(self) -> str:  # type: ignore[override]
        """Get testnet REST URL for candles.

        :return: Testnet REST URL for candles endpoint
        """
        return f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def _get_testnet_ws_url(self) -> str:  # type: ignore[override]
        """Get testnet WebSocket URL.

        :return: Testnet WebSocket URL
        """
        return SPOT_TESTNET_WSS_URL
