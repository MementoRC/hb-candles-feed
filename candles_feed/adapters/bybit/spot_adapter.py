"""
Bybit spot exchange adapter for the Candle Feed framework.
"""

from typing import Optional

from candles_feed.adapters.bybit.base_adapter import BybitBaseAdapter
from candles_feed.adapters.bybit.constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_config import NetworkConfig


@ExchangeRegistry.register("bybit_spot")
class BybitSpotAdapter(BybitBaseAdapter):
    """Bybit spot exchange adapter."""

    def __init__(self, *args, network_config: Optional[NetworkConfig] = None, **kwargs):
        """Initialize the adapter.

        :param network_config: Network configuration for testnet/production
        :param args: Additional positional arguments
        :param kwargs: Additional keyword arguments
        """
        # Store network_config for potential future use
        self.network_config = network_config
        super().__init__(*args, **kwargs)

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return SPOT_WSS_URL

    def get_category_param(self) -> str:
        """Get the category parameter for the market type.

        :returns: Category parameter string
        """
        return "spot"
