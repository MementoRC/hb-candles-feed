"""
Base OKX adapter implementation for the Candle Feed framework.

This module provides a base implementation for OKX-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod
from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.okx.constants import (
    INTERVAL_TO_OKX_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData


class OKXBaseAdapter(BaseAdapter):
    """Base class for OKX exchange adapters.

    This class provides shared functionality for OKX spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :return: Trading pair in OKX format (e.g., "BTC-USDT")
        """
        return trading_pair

    @abstractmethod
    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        pass

    @abstractmethod
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :return: WebSocket URL
        """
        pass

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
        # OKX uses after and before parameters with timestamps
        params = {
            "instId": trading_pair.replace("-", "/"),
            "bar": INTERVAL_TO_OKX_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if start_time:
            params["after"] = start_time

        if end_time:
            params["before"] = end_time

        return params

    @abstractmethod
    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :return: List of CandleData objects
        """
        pass

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :return: WebSocket subscription payload
        """
        # OKX WebSocket subscription format:
        return {
            "op": "subscribe",
            "args": [
                {
                    "channel": "candle" + INTERVAL_TO_OKX_FORMAT.get(interval, interval),
                    "instId": trading_pair.replace("-", "/"),
                }
            ],
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :return: List of CandleData objects or None if message is not a candle update
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
            candles = []
            for row in data["data"]:
                candles.append(
                    CandleData(
                        timestamp_raw=int(row[0]) / 1000,  # Convert milliseconds to seconds
                        open=float(row[1]),
                        high=float(row[2]),
                        low=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[5]),
                        quote_asset_volume=float(row[6]) if row[6] != "0" else 0.0,
                    )
                )
            return candles

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
