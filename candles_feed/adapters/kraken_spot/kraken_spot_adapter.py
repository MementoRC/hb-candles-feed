"""
Kraken spot exchange adapter for the Candle Feed framework.
"""

from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.kraken_spot.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_KRAKEN_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("kraken_spot")
class KrakenSpotAdapter(BaseAdapter):
    """Kraken spot exchange adapter."""

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")

        Returns:
            Trading pair in Kraken format (e.g., "XBTUSD" for "BTC-USD")
        """
        # Kraken has some special cases
        base, quote = trading_pair.split("-")

        # Handle special cases
        if base == "BTC":
            base = "XBT"
        if quote == "USDT":
            quote = "USD"

        # For major currencies, Kraken adds X/Z prefix
        if base in ["XBT", "ETH", "LTC", "XMR", "XRP", "ZEC"]:
            base = "X" + base
        if quote in ["USD", "EUR", "GBP", "JPY", "CAD"]:
            quote = "Z" + quote

        return base + quote

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        return WSS_URL

    def get_rest_params(self,
                      trading_pair: str,
                      interval: str,
                      start_time: Optional[int] = None,
                      end_time: Optional[int] = None,
                      limit: Optional[int] = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST) -> dict:
        """Get parameters for REST API request.

        Args:
            trading_pair: Trading pair
            interval: Candle interval
            start_time: Start time in seconds
            end_time: End time in seconds
            limit: Maximum number of candles to return

        Returns:
            Dictionary of parameters for REST API request
        """
        # Kraken uses 'pair', 'interval' in minutes, and 'since' parameter
        params = {
            "pair": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_KRAKEN_FORMAT.get(interval, 1)  # Default to 1m
        }

        if start_time:
            params["since"] = start_time

        return params

    def parse_rest_response(self, data: dict) -> List[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        # Kraken candle format:
        # {
        #   "error": [],
        #   "result": {
        #     "XXBTZUSD": [
        #       [
        #         1616662800,     // Time
        #         "52556.5",      // Open
        #         "52650.0",      // High
        #         "52450.0",      // Low
        #         "52483.4",      // Close
        #         "52519.9",      // VWAP
        #         "56.72067891",  // Volume
        #         158             // Count
        #       ],
        #       ...
        #     ],
        #     "last": 1616691600
        #   }
        # }

        candles = []
        # Extract the actual data, which is under the pair name
        for pair_data in data.get("result", {}).values():
            if isinstance(pair_data, list):
                for row in pair_data:
                    candles.append(CandleData(
                        timestamp_raw=int(row[0]),  # Already in seconds
                        open=float(row[1]),
                        high=float(row[2]),
                        low=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[6]),
                        quote_asset_volume=float(row[6]) * float(row[5]),  # Volume * VWAP
                        n_trades=int(row[7])
                    ))
        return candles

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        Args:
            trading_pair: Trading pair
            interval: Candle interval

        Returns:
            WebSocket subscription payload
        """
        # Kraken WebSocket subscription format:
        return {
            "name": "subscribe",
            "reqid": 1,
            "pair": [self.get_trading_pair_format(trading_pair)],
            "subscription": {
                "name": "ohlc",
                "interval": INTERVAL_TO_KRAKEN_FORMAT.get(interval, 1)  # Default to 1m
            }
        }

    def parse_ws_message(self, data: dict) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        # Kraken WebSocket message format:
        # [
        #   0,                    // ChannelID
        #   [
        #     "1542057314.748456", // Time
        #     "1542057360.435743", // End
        #     "3586.70000",       // Open
        #     "3586.70000",       // High
        #     "3586.60000",       // Low
        #     "3586.60000",       // Close
        #     "3586.68894",       // VWAP
        #     "0.03373000",       // Volume
        #     2                   // Count
        #   ],
        #   "ohlc-1",            // Channel name with interval
        #   "XBT/USD"            // Pair
        # ]

        # Check if this is a candle update (array with 4 elements, channel name starting with "ohlc-")
        if (isinstance(data, list) and len(data) == 4 and
            isinstance(data[2], str) and data[2].startswith("ohlc-") and
            isinstance(data[1], list) and len(data[1]) >= 8):

            candle_data = data[1]
            return [CandleData(
                timestamp_raw=float(candle_data[0]),  # Time in seconds
                open=float(candle_data[2]),
                high=float(candle_data[3]),
                low=float(candle_data[4]),
                close=float(candle_data[5]),
                volume=float(candle_data[7]),
                quote_asset_volume=float(candle_data[7]) * float(candle_data[6]),  # Volume * VWAP
                n_trades=int(candle_data[8]) if len(candle_data) > 8 else 0
            )]

        return None

    def get_supported_intervals(self) -> Dict[str, int]:
        """Get supported intervals and their durations in seconds.

        Returns:
            Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> List[str]:
        """Get intervals supported by WebSocket API.

        Returns:
            List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS
