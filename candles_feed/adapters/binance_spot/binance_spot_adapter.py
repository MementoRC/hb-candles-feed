"""
Binance spot exchange adapter for the Candle Feed V2 framework.
"""

from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.binance_spot.constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("binance_spot")
class BinanceSpotAdapter(BaseAdapter):
    """Binance spot exchange adapter."""

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")

        Returns:
            Trading pair in Binance format (e.g., "BTCUSDT")
        """
        return trading_pair.replace("-", "")

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        return REST_URL

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
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": interval,
            "limit": limit
        }

        if start_time:
            params["startTime"] = start_time * 1000  # Convert to milliseconds
        if end_time:
            params["endTime"] = end_time * 1000      # Convert to milliseconds

        return params

    def parse_rest_response(self, data: list) -> List[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        # Binance candle format:
        # [
        #   [
        #     1499040000000,      // Open time
        #     "0.01634790",       // Open
        #     "0.80000000",       // High
        #     "0.01575800",       // Low
        #     "0.01577100",       // Close
        #     "148976.11427815",  // Volume
        #     1499644799999,      // Close time
        #     "2434.19055334",    // Quote asset volume
        #     308,                // Number of trades
        #     "1756.87402397",    // Taker buy base asset volume
        #     "28.46694368",      // Taker buy quote asset volume
        #     "17928899.62484339" // Ignore.
        #   ]
        # ]

        candles = []
        for row in data:
            candles.append(CandleData(
                timestamp_raw=row[0] / 1000,  # Convert from milliseconds
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_asset_volume=float(row[7]),
                n_trades=int(row[8]),
                taker_buy_base_volume=float(row[9]),
                taker_buy_quote_volume=float(row[10])
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
        return {
            "method": "SUBSCRIBE",
            "params": [f"{self.get_trading_pair_format(trading_pair).lower()}@kline_{interval}"],
            "id": 1
        }

    def parse_ws_message(self, data: dict) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        # Binance WS candle format:
        # {
        #   "e": "kline",     // Event type
        #   "E": 123456789,   // Event time
        #   "s": "BTCUSDT",   // Symbol
        #   "k": {
        #     "t": 123400000, // Kline start time
        #     "T": 123460000, // Kline close time
        #     "s": "BTCUSDT", // Symbol
        #     "i": "1m",      // Interval
        #     "f": 100,       // First trade ID
        #     "L": 200,       // Last trade ID
        #     "o": "0.0010",  // Open price
        #     "c": "0.0020",  // Close price
        #     "h": "0.0025",  // High price
        #     "l": "0.0015",  // Low price
        #     "v": "1000",    // Base asset volume
        #     "n": 100,       // Number of trades
        #     "x": false,     // Is this kline closed?
        #     "q": "1.0000",  // Quote asset volume
        #     "V": "500",     // Taker buy base asset volume
        #     "Q": "0.500",   // Taker buy quote asset volume
        #     "B": "123456"   // Ignore
        #   }
        # }

        if data is not None and data.get("e") == "kline":
            return [CandleData(
                timestamp_raw=data["k"]["t"] / 1000,  # Convert from milliseconds
                open=float(data["k"]["o"]),
                high=float(data["k"]["h"]),
                low=float(data["k"]["l"]),
                close=float(data["k"]["c"]),
                volume=float(data["k"]["v"]),
                quote_asset_volume=float(data["k"]["q"]),
                n_trades=int(data["k"]["n"]),
                taker_buy_base_volume=float(data["k"]["V"]),
                taker_buy_quote_volume=float(data["k"]["Q"])
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
