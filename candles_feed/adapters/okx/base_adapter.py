"""
Base OKX adapter implementation for the Candle Feed framework.

This module provides a base implementation for OKX-based exchange adapters
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


class OKXBaseAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Base class for OKX exchange adapters.

    This class provides shared functionality for OKX spot and perpetual adapters.
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
        :returns: Trading pair in OKX format (e.g., "BTC-USDT")
        """
        return trading_pair

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
        # OKX uses after and before parameters with timestamps
        params: dict[str, str | int] = {  # type: ignore
            "instId": self.get_trading_pair_format(
                trading_pair
            ),  # OKX format (spot uses BTC-USDT, perpetual uses BTC-USDT-SWAP)
            "bar": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if start_time:
            # OKX 'after' is for data after this timestamp (exclusive for newer data, inclusive for older data if 'before' is not set)
            # OKX 'before' is for data before this timestamp (exclusive for older data)
            # To get data starting from 'start_time', we might need to use 'after' carefully or adjust.
            # If start_time means "inclusive start", then 'after' should be start_time - interval_duration,
            # or rely on 'limit' to fetch enough data to cover the start_time.
            # For simplicity, directly using start_time for 'after'.
            # The API typically wants 'after' for pagination of older data (cursor is the oldest ts)
            # and 'before' for newer data (cursor is the newest ts).
            # If 'start_time' means "fetch candles whose timestamp is >= start_time",
            # OKX's 'after' (for older data) or 'before' (for newer data) needs careful handling.
            # Given _fetch_rest_candles logic, start_time is for older data.
            # So 'after' should be used if start_time means "fetch data older than this".
            # However, the common interpretation of start_time is "fetch data from this time onwards".
            # OKX REST API: "after: Request data after this timestamp" (newer data).
            # "before: Request data before this timestamp" (older data).
            # If we want data from a historical start_time up to now (or a limit), we'd use 'before' with start_time.
            # This seems reversed from typical 'start_time' usage.
            # Let's assume start_time is used to get data *before* this timestamp (i.e., older data).
            params["before"] = self.convert_timestamp_to_exchange(start_time)

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        # OKX perpetual candle format:
        # [
        #   [
        #     "1597026383085",   // Time
        #     "11966.47",        // Open
        #     "11966.48",        // High
        #     "11966.46",        // Low
        #     "11966.48",        // Close
        #     "0.0608",          // Volume
        #     "727.3"            // Quote Asset Volume
        #   ],
        #   ...
        # ]

        if data is None:
            return []

        if not isinstance(data, dict) or "data" not in data:
            return []

        candle_list_payload = data["data"]
        if not isinstance(candle_list_payload, list):
            return []

        candles: list[CandleData] = []
        candles.extend(
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_asset_volume=float(row[6]) if len(row) > 6 and row[6] is not None else 0.0,
            )
            for row in candle_list_payload
            if isinstance(row, list) and len(row) >= 6  # Ensure row is list and has enough items
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
        # OKX WebSocket subscription format:
        return {  # type: ignore
            "op": "subscribe",  # type: ignore
            "args": [  # type: ignore
                {  # type: ignore
                    "channel": f"candle{INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)}",  # type: ignore
                    "instId": OKXBaseAdapter.get_trading_pair_format(trading_pair).replace(
                        "-", "/"
                    ),  # type: ignore
                }
            ],
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        # OKX WebSocket message format:
        # {
        #   "arg": {
        #     "channel": "candle1m",
        #     "instId": "BTC-USDT"
        #   },
        #   "data": [
        #     [
        #       "1597026383085",   // Time
        #       "11966.47",        // Open
        #       "11966.48",        // High
        #       "11966.46",        // Low
        #       "11966.48",        // Close
        #       "0.0608",          // Volume
        #       "0"                // Currency Volume (empty field on spot)
        #     ]
        #   ]
        # }

        # Data will be None when the websocket is disconnected
        if data is None:
            return None

        if "data" in data and isinstance(data["data"], list):
            candle_list_payload = data["data"]
            parsed_candles: list[CandleData] = []
            for row_payload in candle_list_payload:
                if isinstance(row_payload, list) and len(row_payload) >= 7:
                    parsed_candles.append(
                        CandleData(
                            timestamp_raw=self.ensure_timestamp_in_seconds(row_payload[0]),
                            open=float(row_payload[1]),
                            high=float(row_payload[2]),
                            low=float(row_payload[3]),
                            close=float(row_payload[4]),
                            volume=float(row_payload[5]),
                            quote_asset_volume=float(row_payload[6])
                            if row_payload[6] != "0"
                            else 0.0,
                        )
                    )
            return parsed_candles

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
