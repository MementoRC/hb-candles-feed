"""
KuCoin Spot plugin implementation for the mock exchange server.
"""

from candles_feed.core.candle_data import CandleData
from candles_feed.adapters.kucoin.spot_adapter import KucoinSpotAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.kucoin.base_plugin import KucoinBasePlugin


class KucoinSpotPlugin(KucoinBasePlugin):
    """
    KuCoin Spot plugin for the mock exchange server.

    This plugin implements the KuCoin Spot API for the mock server,
    translating between the standardized mock server format and the
    KuCoin-specific formats.
    """

    def __init__(self):
        """
        Initialize the KuCoin Spot plugin.
        """
        super().__init__(ExchangeType.KUCOIN_SPOT, KucoinSpotAdapter)

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for KuCoin Spot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/v1/market/candles": ("GET", "handle_klines"),
            "/api/v1/timestamp": ("GET", "handle_time"),
            "/api/v1/symbols": ("GET", "handle_instruments"),
        }

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as a KuCoin Spot REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from KuCoin's REST API.
        """
        return super().format_rest_candles(candles, trading_pair, interval)