"""
Base Bybit adapter implementation for the Candle Feed framework.

This module provides a base implementation for Bybit-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)


class BybitBaseAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Base class for Bybit exchange adapters.

    This class provides shared functionality for Bybit spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    TIMESTAMP_UNIT: str = "milliseconds"

    @abstractmethod
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        pass

    @abstractmethod
    def _get_ws_url(self) -> str:
        """Get WebSocket URL (internal implementation).

        :returns: WebSocket URL
        """
        pass

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return self._get_ws_url()

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in Bybit format (e.g., "BTCUSDT")
        """
        return trading_pair.replace("-", "")

    @abstractmethod
    def get_category_param(self) -> str:
        """Get the category parameter for the market type.

        :returns: Category parameter string
        """
        pass

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: Dictionary of parameters for REST API request
        """
        # Bybit uses startTime and endTime parameters with timestamps in milliseconds
        params: dict[str, str | int] = {  # type: ignore
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if category := self.get_category_param():
            params["category"] = category  # type: ignore

        if start_time:
            params["start"] = self.convert_timestamp_to_exchange(start_time)  # type: ignore

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects
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

        if data is None:
            return []

        assert isinstance(data, dict), f"Unexpected data type: {type(data)}"
        result_data = data.get("result", {})
        assert isinstance(result_data, dict), "result field is not a dict"
        candle_list_data = result_data.get("list", [])
        assert isinstance(candle_list_data, list), "list field is not a list"

        candles: list[CandleData] = []
        candles.extend(
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_asset_volume=float(row[6]),
            )
            for row in candle_list_data
        )
        return candles

    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles from REST API asynchronously.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :param network_client: Network client to use for API requests
        :returns: List of CandleData objects
        """
        return await AsyncOnlyAdapter._fetch_rest_candles(
            adapter_implementation=self,
            trading_pair=trading_pair,
            interval=interval,
            start_time=start_time,
            limit=limit,
            network_client=network_client,
        )

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :returns: WebSocket subscription payload
        """
        # Bybit WebSocket subscription format:
        return {
            "op": "subscribe",
            "args": [
                f"kline.{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}.{self.get_trading_pair_format(trading_pair)}"
            ],
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
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

        if (
            "topic" in data
            and isinstance(data["topic"], str)
            and data["topic"].startswith("kline.")
            and "data" in data
        ):
            candle_items = data["data"]
            if isinstance(candle_items, list):
                candles: list[CandleData] = []
                for item in candle_items:
                    if isinstance(item, dict):
                        candles.append(
                            CandleData(
                                timestamp_raw=self.ensure_timestamp_in_seconds(item["start"]),
                                open=float(item["open"]),
                                high=float(item["high"]),
                                low=float(item["low"]),
                                close=float(item["close"]),
                                volume=float(item["volume"]),
                                quote_asset_volume=float(item["turnover"]),
                            )
                        )
                return candles

        return None

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS
