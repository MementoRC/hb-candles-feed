"""
Bitget Spot plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.bitget.constants import SPOT_CANDLES_ENDPOINT, SPOT_INTERVAL_TO_EXCHANGE
from candles_feed.adapters.bitget.spot_adapter import BitgetSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_type import ExchangeType

from .base_plugin import BitgetBasePlugin


class BitgetSpotPlugin(BitgetBasePlugin):
    """
    Bitget Spot plugin for the mock exchange server.

    Spot REST candles carry an eighth column (quote volume in USDT) that the adapter reads.
    """

    def __init__(self):
        """
        Initialize the Bitget Spot plugin.
        """
        super().__init__(
            ExchangeType.BITGET_SPOT, BitgetSpotAdapter, SPOT_INTERVAL_TO_EXCHANGE, "SPOT"
        )

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for Bitget Spot.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {SPOT_CANDLES_ENDPOINT: ("GET", "handle_klines")}

    def format_rest_candles(
        self,
        candles: list[CandleData],
        trading_pair: str,
        interval: str,
        timezone_adjustment_ms: int = 0,
    ) -> dict:
        """
        Format candle data as a Bitget Spot REST API response (8 columns per candle).

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param timezone_adjustment_ms: Unused; accepted for server compatibility.
        :returns: Formatted response as expected from Bitget's REST API.
        """
        response = super().format_rest_candles(
            candles, trading_pair, interval, timezone_adjustment_ms
        )
        for row, candle in zip(response["data"], candles, strict=True):
            row.append(str(candle.quote_asset_volume))
        return response
