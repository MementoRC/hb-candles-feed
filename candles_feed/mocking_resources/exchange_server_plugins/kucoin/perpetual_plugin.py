"""
KuCoin Perpetual plugin implementation for the mock exchange server.
"""

from typing import Any
from aiohttp import web
from candles_feed.core.candle_data import CandleData
from candles_feed.adapters.kucoin.constants import PERPETUAL_WSS_URL, INTERVAL_TO_EXCHANGE_FORMAT
from candles_feed.adapters.kucoin.perpetual_adapter import KucoinPerpetualAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.kucoin.base_plugin import KucoinBasePlugin


class KucoinPerpetualPlugin(KucoinBasePlugin):
    """
    KuCoin Perpetual plugin for the mock exchange server.

    This plugin implements the KuCoin Perpetual API for the mock server,
    translating between the standardized mock server format and the
    KuCoin-specific formats.
    """

    def __init__(self):
        """
        Initialize the KuCoin Perpetual plugin.
        """
        super().__init__(ExchangeType.KUCOIN_PERPETUAL, KucoinPerpetualAdapter)

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for KuCoin Perpetual.

        :returns: The base WebSocket API URL.
        """
        return PERPETUAL_WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for KuCoin Perpetual.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/v1/kline/query": ("GET", "handle_klines"),
            "/api/v1/timestamp": ("GET", "handle_time"),
            "/api/v1/contracts/active": ("GET", "handle_instruments"),
        }

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as a KuCoin Perpetual REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from KuCoin's REST API.
        """
        # For perpetual futures, the response format is slightly different
        # Format candles for perpetual futures API
        candle_data = [
            [
                int(c.timestamp_ms),              # Timestamp in milliseconds
                str(c.open),                      # Open price
                str(c.high),                      # High price
                str(c.low),                       # Low price
                str(c.close),                     # Close price
                str(c.volume),                    # Volume
                str(c.quote_asset_volume)         # Quote volume
            ]
            for c in candles
        ]

        return {
            "code": "200000",
            "data": {
                "dataList": candle_data,
                "symbol": trading_pair,
                "granularity": interval
            }
        }
        
    def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
        """
        Parse REST API parameters for KuCoin Perpetual candle requests.

        :param request: The web request.
        :returns: A dictionary with standardized parameter names.
        """
        params = request.query
        
        # Convert KuCoin-specific parameter names to the generic ones expected by handle_klines
        symbol = params.get("symbol")
        interval = params.get("granularity", "1min")
        start_time = params.get("from")
        end_time = params.get("to")
        
        # KuCoin may have a limit parameter
        limit = 200  # Default limit is 200 for perpetual futures
                
        # Map KuCoin parameters to generic parameters expected by handle_klines
        return {
            "symbol": symbol,
            "interval": next((k for k, v in INTERVAL_TO_EXCHANGE_FORMAT.items() if v == interval), interval),
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        }