"""
MEXC Perpetual plugin implementation for the mock exchange server.
"""

from candles_feed.adapters.mexc.constants import PERP_WSS_URL, PERP_REST_URL, INTERVAL_TO_PERPETUAL_FORMAT
from candles_feed.adapters.mexc.perpetual_adapter import MEXCPerpetualAdapter
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.mexc.base_plugin import MEXCBasePlugin
from candles_feed.core.candle_data import CandleData


class MEXCPerpetualPlugin(MEXCBasePlugin):
    """
    MEXC Perpetual plugin for the mock exchange server.

    This plugin implements the MEXC Perpetual API for the mock server,
    translating between the standardized mock server format and the
    MEXC-specific formats.
    """

    def __init__(self):
        """
        Initialize the MEXC Perpetual plugin.
        """
        super().__init__(ExchangeType.MEXC_PERPETUAL, MEXCPerpetualAdapter)

    @property
    def rest_url(self) -> str:
        """
        Get the base REST API URL for MEXC Perpetual.

        :returns: The base REST API URL.
        """
        return PERP_REST_URL

    @property
    def wss_url(self) -> str:
        """
        Get the base WebSocket API URL for MEXC Perpetual.

        :returns: The base WebSocket API URL.
        """
        return PERP_WSS_URL

    @property
    def rest_routes(self) -> dict[str, tuple[str, str]]:
        """
        Get the REST API routes for MEXC Perpetual.

        :returns: A dictionary mapping URL paths to tuples of (HTTP method, handler name).
        """
        return {
            "/api/v1/contract/ping": ("GET", "handle_ping"),
            "/api/v1/contract/kline": ("GET", "handle_klines"),
            "/api/v1/contract/time": ("GET", "handle_time"),
            "/api/v1/contract/detail": ("GET", "handle_instruments"),
        }

    def format_rest_candles(
        self, candles: list[CandleData], trading_pair: str, interval: str
    ) -> dict:
        """
        Format candle data as a MEXC Perpetual REST API response.

        :param candles: List of candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :returns: Formatted response as expected from MEXC Perpetual's REST API.
        """
        # MEXC Contract API returns a different format than spot
        formatted_candles = []
        for c in candles:
            formatted_candles.append({
                "time": int(c.timestamp_ms / 1000),  # Contract API uses seconds
                "open": str(c.open),
                "close": str(c.close),
                "high": str(c.high),
                "low": str(c.low),
                "vol": str(c.volume),
                "amount": str(c.quote_asset_volume)
            })
            
        return {
            "success": True,
            "code": 0,
            "data": formatted_candles
        }

    def format_ws_candle_message(
        self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
    ) -> dict:
        """
        Format candle data as a MEXC Perpetual WebSocket message.

        :param candle: Candle data to format.
        :param trading_pair: The trading pair.
        :param interval: The candle interval.
        :param is_final: Whether this is the final update for this candle.
        :returns: Formatted message as expected from MEXC Perpetual's WebSocket API.
        """
        # INTERVAL_TO_PERPETUAL_FORMAT is now imported at the module level
        
        # Format for MEXC Perpetual WebSocket API
        symbol = trading_pair.replace("-", "_")
        mexc_interval = INTERVAL_TO_PERPETUAL_FORMAT.get(interval, interval)
        
        return {
            "channel": "push.kline",
            "data": {
                "symbol": symbol,
                "interval": mexc_interval,
                "t": int(candle.timestamp_ms / 1000),  # Perpetual uses seconds
                "o": str(candle.open),
                "h": str(candle.high),
                "l": str(candle.low),
                "c": str(candle.close),
                "v": str(candle.volume),
                "a": str(candle.quote_asset_volume),
                "q": "0"  # Ignore
            },
            "symbol": symbol
        }