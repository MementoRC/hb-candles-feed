"""
Bitget Perpetual plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.bitget.constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_INTERVAL_TO_EXCHANGE,
)
from candles_feed.adapters.bitget.perpetual_adapter import BitgetPerpetualAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType

from .base_plugin import BitgetBasePlugin


class BitgetPerpetualPlugin(BitgetBasePlugin):
    """
    Bitget Perpetual plugin for the mock exchange server.

    Serves USDT-margined futures candles (``USDT-FUTURES`` product type).
    """

    def __init__(self):
        """
        Initialize the Bitget Perpetual plugin.
        """
        super().__init__(
            ExchangeType.BITGET_PERPETUAL,
            BitgetPerpetualAdapter,
            PERPETUAL_INTERVAL_TO_EXCHANGE,
            "USDT-FUTURES",
        )

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Bitget Perpetual.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {PERPETUAL_CANDLES_ENDPOINT: ("GET", "handle_klines")}
