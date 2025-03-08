"""
Base Gate.io adapter implementation for the Candle Feed framework.

This module provides a base implementation for Gate.io-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod, ABC

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.gate_io.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData


class GateIoBaseAdapter(BaseAdapter, ABC):
    """Base class for Gate.io exchange adapters.

    This class provides shared functionality for Gate.io spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    TIMESTAMP_UNIT: str = "seconds"
    
    @staticmethod
    @abstractmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.
        
        :return: REST API URL
        """
        pass
        
    @staticmethod
    @abstractmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.
        
        :return: WebSocket URL
        """
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :return: Channel name string
        """
        pass

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :return: Trading pair in Gate.io format (e.g., "BTC_USDT")
        """
        return trading_pair.replace("-", "_")

    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param end_time: End time in seconds
        :param limit: Maximum number of candles to return
        :return: Dictionary of parameters for REST API request
        """
        params = {
            "currency_pair": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if start_time:
            params["from"] = self.convert_timestamp_to_exchange(start_time)
        if end_time:
            params["to"] = self.convert_timestamp_to_exchange(end_time)

        return params

    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :return: List of CandleData objects
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
        candles.extend(
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
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
            for row in data
        )
        return candles

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :return: WebSocket subscription payload
        """
        # Gate.io WebSocket subscription format
        return {
            "method": "subscribe",
            "params": [
                f"{self.get_channel_name()}",
                {
                    "currency_pair": self.get_trading_pair_format(trading_pair),
                    "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
                },
            ],
            "id": 12345,
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :return: List of CandleData objects or None if message is not a candle update
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
                    timestamp_raw=self.ensure_timestamp_in_seconds(candle_data[0]),
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

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :return: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :return: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS
