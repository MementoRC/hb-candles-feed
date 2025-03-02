"""
Bybit spot exchange adapter for the Candle Feed framework.
"""

from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.bybit_spot.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_BYBIT_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("bybit_spot")
class BybitSpotAdapter(BaseAdapter):
    """Bybit spot exchange adapter."""

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")

        Returns:
            Trading pair in Bybit format (e.g., "BTCUSDT")
        """
        return trading_pair.replace("-", "")

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
        # Bybit uses startTime and endTime parameters with timestamps in milliseconds
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_BYBIT_FORMAT.get(interval, interval),
            "limit": limit
        }

        if start_time:
            params["start"] = start_time * 1000  # Convert seconds to milliseconds

        if end_time:
            params["end"] = end_time * 1000  # Convert seconds to milliseconds

        return params

    def parse_rest_response(self, data: dict) -> List[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        # Bybit candle format:
        # {
        #   "result": {
        #     "category": "spot",
        #     "symbol": "BTCUSDT",
        #     "list": [
        #       [
        #         "1659398400000",  // Timestamp (ms)
        #         "23409.33",       // Open price
        #         "23497.07",       // High price
        #         "23214.69",       // Low price
        #         "23388.73",       // Close price
        #         "886.196394",     // Volume
        #         "20800649.5919274" // Turnover
        #       ]
        #     ]
        #   }
        # }

        candles = []
        for row in data.get("result", {}).get("list", []):
            candles.append(CandleData(
                timestamp_raw=int(row[0]) / 1000,  # Convert milliseconds to seconds
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_asset_volume=float(row[6])
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
        # Bybit WebSocket subscription format:
        return {
            "op": "subscribe",
            "args": [
                f"kline.{INTERVAL_TO_BYBIT_FORMAT.get(interval, interval)}.{self.get_trading_pair_format(trading_pair)}"
            ]
        }

    def parse_ws_message(self, data: Optional[dict]) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        # Bybit WebSocket message format:
        # {
        #   "topic": "kline.1.BTCUSDT",
        #   "data": [
        #     {
        #       "start": 1659398400000,  // Timestamp (ms)
        #       "end": 1659398460000,
        #       "interval": "1",
        #       "open": "23409.33",      // Open price
        #       "close": "23388.73",     // Close price
        #       "high": "23497.07",      // High price
        #       "low": "23214.69",       // Low price
        #       "volume": "886.196394",  // Volume
        #       "turnover": "20800649.5919274", // Turnover
        #       "confirm": false,
        #       "timestamp": 1659398459000
        #     }
        #   ],
        #   "ts": 1659398459102,
        #   "type": "snapshot"
        # }

        if data is None:
            return None
            
        if "topic" in data and data["topic"].startswith("kline.") and "data" in data:
            candles = []
            for item in data["data"]:
                candles.append(CandleData(
                    timestamp_raw=item["start"] / 1000,  # Convert milliseconds to seconds
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    volume=float(item["volume"]),
                    quote_asset_volume=float(item["turnover"])
                ))
            return candles

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
