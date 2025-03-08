"""
OKX perpetual exchange adapter for the Candle Feed framework.
"""

from candles_feed.adapters.okx.base_adapter import OKXBaseAdapter
from candles_feed.adapters.okx.constants import (
    PERP_CANDLES_ENDPOINT,
    PERP_REST_URL,
    PERP_WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("okx_perpetual")
class OKXPerpetualAdapter(OKXBaseAdapter):
    """OKX perpetual exchange adapter."""

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        For perpetual contracts, OKX requires the SWAP suffix to be added.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :return: Trading pair in OKX perpetual format (e.g., "BTC-USDT-SWAP")
        """
        # If the trading pair already has the SWAP suffix, return it as is
        if trading_pair.endswith("-SWAP"):
            return trading_pair
        return f"{trading_pair}-SWAP"

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return f"{PERP_REST_URL}{PERP_CANDLES_ENDPOINT}"

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        return PERP_WSS_URL
