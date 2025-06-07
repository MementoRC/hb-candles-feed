"""
Kraken Spot plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.kraken.constants import SPOT_CANDLES_ENDPOINT, TIME_ENDPOINT
from candles_feed.adapters.kraken.spot_adapter import KrakenSpotAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.kraken.base_plugin import (
    KrakenBasePlugin,
)


class KrakenSpotPlugin(KrakenBasePlugin):
    """
    Kraken Spot plugin for the mock exchange server.

    This plugin implements the Kraken Spot API for the mock server,
    translating between the standardized mock server format and the
    Kraken-specific formats.
    """

    def __init__(self):
        """
        Initialize the Kraken Spot plugin.
        """
        super().__init__(ExchangeType.KRAKEN_SPOT, KrakenSpotAdapter)

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Kraken Spot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            SPOT_CANDLES_ENDPOINT: ("GET", "handle_klines"),
            TIME_ENDPOINT: ("GET", "handle_time"),
        }
