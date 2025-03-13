"""
AscendEx Spot plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.ascend_ex.spot_adapter import AscendExSpotAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from .base_plugin import AscendExBasePlugin


class AscendExSpotPlugin(AscendExBasePlugin):
    """
    AscendEx Spot plugin for the mock exchange server.

    This plugin implements the AscendEx Spot API for the mock server,
    translating between the standardized mock server format and the
    AscendEx-specific formats.
    """

    def __init__(self):
        """
        Initialize the AscendEx Spot plugin.
        """
        super().__init__(ExchangeType.ASCEND_EX_SPOT, AscendExSpotAdapter)

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for AscendEx Spot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/pro/v1/barhist": ("GET", "handle_klines"),
            "/api/pro/v1/risk-limit-info": ("GET", "handle_time"),
            "/api/pro/v1/products": ("GET", "handle_instruments"),
        }