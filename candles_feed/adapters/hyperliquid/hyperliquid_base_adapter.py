"""
Base HyperLiquid adapter implementation for the Candle Feed framework.

This module provides a base implementation for HyperLiquid-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod
from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.hyperliquid.constants import (
    CHANNEL_NAME,
    INTERVAL_TO_HYPERLIQUID_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData


class HyperliquidBaseAdapter(BaseAdapter):
    """Base class for HyperLiquid exchange adapters.

    This class provides shared functionality for HyperLiquid spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :return: Trading pair in HyperLiquid format (e.g., "BTC")
        """
        # HyperLiquid uses just the base asset as the "coin" symbol
        base, _ = trading_pair.split("-", 1)
        return base

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
        # HyperLiquid uses a POST request with JSON body
        coin = self.get_trading_pair_format(trading_pair)

        params = {
            "type": "candles",
            "coin": coin,
            "resolution": INTERVAL_TO_HYPERLIQUID_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        return params

    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :return: List of CandleData objects
        """
        if data is None or not isinstance(data, list):
            return []

        return [
            CandleData(
                timestamp_raw=candle[0],
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5]),
                quote_asset_volume=float(candle[6]),
                n_trades=0,  # Not provided by HyperLiquid
                taker_buy_base_volume=0.0,  # Not provided
                taker_buy_quote_volume=0.0,  # Not provided
            )
            for candle in data
            if len(candle) >= 7
        ]

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :return: WebSocket subscription payload
        """
        coin = self.get_trading_pair_format(trading_pair)

        return {
            "method": "subscribe",
            "channel": CHANNEL_NAME,
            "coin": coin,
            "interval": INTERVAL_TO_HYPERLIQUID_FORMAT.get(interval, interval),
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :return: List of CandleData objects or None if message is not a candle update
        """
        if data is None:
            return None

        # Check if this is a candle message
        if data.get("channel") == CHANNEL_NAME and "data" in data:
            candle = data["data"]

            if isinstance(candle, list) and len(candle) >= 7:
                return [
                    CandleData(
                        timestamp_raw=candle[0],
                        open=float(candle[1]),
                        high=float(candle[2]),
                        low=float(candle[3]),
                        close=float(candle[4]),
                        volume=float(candle[5]),
                        quote_asset_volume=float(candle[6]),
                        n_trades=0,  # Not provided by HyperLiquid
                        taker_buy_base_volume=0.0,  # Not provided
                        taker_buy_quote_volume=0.0,  # Not provided
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
