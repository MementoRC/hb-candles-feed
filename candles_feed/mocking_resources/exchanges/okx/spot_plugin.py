from candles_feed.adapters.okx.spot_adapter import OKXSpotAdapter

from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchanges.okx.base_plugin import OKXBasePlugin


class OKXSpotPlugin(OKXBasePlugin):
    """
    OKX plugin for the mock exchange server.

    This plugin implements the OKX Spot API for the mock server.
    """

    def __init__(self):
        """
        Initialize the OKX plugin.
        """
        super().__init__(ExchangeType.OKX_SPOT, OKXSpotAdapter)

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for OKX.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/v5/market/candles": ("GET", "handle_klines"),
            "/api/v5/public/time": ("GET", "handle_time"),
            "/api/v5/public/instruments": ("GET", "handle_instruments"),
        }
