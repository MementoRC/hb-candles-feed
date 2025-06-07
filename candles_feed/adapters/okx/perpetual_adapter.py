"""
OKX perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import OKXBaseAdapter
from .constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)


@ExchangeRegistry.register("okx_perpetual")
class OKXPerpetualAdapter(OKXBaseAdapter):
    """OKX perpetual exchange adapter."""

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:  # type: ignore[override]
        """Convert standard trading pair format to exchange format.

        For perpetual contracts, OKX requires the SWAP suffix to be added.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in OKX perpetual format (e.g., "BTC-USDT-SWAP")
        """
        # If the trading pair already has the SWAP suffix, return it as is
        if trading_pair.endswith("-SWAP"):
            return trading_pair
        return f"{trading_pair}-SWAP"

    def _get_rest_url(self) -> str:  # type: ignore[override]
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"

    def _get_ws_url(self) -> str:  # type: ignore[override]
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return PERPETUAL_WSS_URL
