"""
Base Gate.io adapter implementation for the Candle Feed framework.

This module provides a base implementation for Gate.io-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod
from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.gate_io.constants import (
    INTERVAL_TO_GATE_IO_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData


class GateIoBaseAdapter(BaseAdapter):
    """Base class for Gate.io exchange adapters.

    This class provides shared functionality for Gate.io spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")

        Returns:
            Trading pair in Gate.io format (e.g., "BTC_USDT")
        """
        return trading_pair.replace("-", "_")

    @abstractmethod
    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        pass

    @abstractmethod
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        Returns:
            Channel name string
        """
        pass

    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict:
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
            "currency_pair": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_GATE_IO_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if start_time:
            params["from"] = start_time
        if end_time:
            params["to"] = end_time

        return params

    def parse_rest_response(self, data: Optional[list]) -> List[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        # Gate.io candle format:
        # [
        #   [
        #     "1626770400",  // timestamp
        #     "29932.21",    // open
        #     "30326.37",    // close
        #     "29586.26",    // low
        #     "30549.57",    // high
        #     "2501.976433", // volume
        #     "74626209.16", // quote currency volume
        #     "BTC_USDT"     // currency pair
        #   ],
        #   ...
        # ]

        if data is None:
            return []

        candles = []
        for row in data:
            candles.append(
                CandleData(
                    timestamp_raw=float(row[0]),
                    open=float(row[1]),
                    high=float(row[4]),  # Gate.io has high at index 4
                    low=float(row[3]),  # Gate.io has low at index 3
                    close=float(row[2]),
                    volume=float(row[5]),
                    quote_asset_volume=float(row[6]),
                    n_trades=0,  # No trade count data available
                    taker_buy_base_volume=0.0,  # No taker data available
                    taker_buy_quote_volume=0.0,  # No taker data available
                )
            )
        return candles

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        Args:
            trading_pair: Trading pair
            interval: Candle interval

        Returns:
            WebSocket subscription payload
        """
        # Gate.io WebSocket subscription format
        return {
            "method": "subscribe",
            "params": [
                f"{self.get_channel_name()}",
                {
                    "currency_pair": self.get_trading_pair_format(trading_pair),
                    "interval": INTERVAL_TO_GATE_IO_FORMAT.get(interval, interval),
                },
            ],
            "id": 12345,
        }

    def parse_ws_message(self, data: Optional[dict]) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        # Handle None input
        if data is None:
            return None

        # Check if this is a candle message
        if (
            isinstance(data, dict)
            and data.get("method") == "update"
            and data.get("channel") == self.get_channel_name()
        ):
            params = data.get("params", [])
            if not params or len(params) < 2:
                return None

            candle_data = params[1]

            # Gate.io WS candle format (similar to REST format):
            # [
            #   "1626770400",  // timestamp
            #   "29932.21",    // open
            #   "30326.37",    // close
            #   "29586.26",    // low
            #   "30549.57",    // high
            #   "2501.976433", // volume
            #   "74626209.16", // quote currency volume
            #   "BTC_USDT"     // currency pair
            # ]

            return [
                CandleData(
                    timestamp_raw=float(candle_data[0]),
                    open=float(candle_data[1]),
                    high=float(candle_data[4]),  # Gate.io has high at index 4
                    low=float(candle_data[3]),  # Gate.io has low at index 3
                    close=float(candle_data[2]),
                    volume=float(candle_data[5]),
                    quote_asset_volume=float(candle_data[6]),
                    n_trades=0,  # No trade count data available
                    taker_buy_base_volume=0.0,  # No taker data available
                    taker_buy_quote_volume=0.0,  # No taker data available
                )
            ]

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
