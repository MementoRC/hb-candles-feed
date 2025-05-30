"""
Base HyperLiquid adapter implementation for the Candle Feed framework.

This module provides a base implementation for HyperLiquid-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod
from typing import Any, Dict, List

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    CHANNEL_NAME,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVALS,
)


class HyperliquidBaseAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Base class for HyperLiquid exchange adapters.

    This class provides shared functionality for HyperLiquid spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    TIMESTAMP_UNIT: str = "seconds"

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
        :returns: Trading pair in HyperLiquid format (e.g., "BTC")
        """
        # HyperLiquid uses just the base asset as the "coin" symbol
        base, _ = trading_pair.split("-", 1)
        return base

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
        # HyperLiquid uses a POST request with JSON body
        coin: str = HyperliquidBaseAdapter.get_trading_pair_format(trading_pair)

        params: dict[str, str | int] = {  # type: ignore
            "type": "candles",
            "coin": coin,
            "resolution": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if start_time:
            params["startTime"] = self.convert_timestamp_to_exchange(start_time)  # type: ignore

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        if data is None or not isinstance(data, list):
            return []

        candles: list[CandleData] = []
        for candle_row in data:
            if isinstance(candle_row, list) and len(candle_row) >= 7:
                candles.append(
                    CandleData(
                        timestamp_raw=self.ensure_timestamp_in_seconds(candle_row[0]),
                        open=float(candle_row[1]),
                        high=float(candle_row[2]),
                        low=float(candle_row[3]),
                        close=float(candle_row[4]),
                        volume=float(candle_row[5]),
                        quote_asset_volume=float(candle_row[6]),
                        n_trades=0,  # Not provided by HyperLiquid
                        taker_buy_base_volume=0.0,  # Not provided
                        taker_buy_quote_volume=0.0,  # Not provided
                    )
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
        coin: str = HyperliquidBaseAdapter.get_trading_pair_format(trading_pair)

        return {
            "method": "subscribe",
            "channel": CHANNEL_NAME,
            "coin": coin,
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        if data is None:
            return None

        # Check if this is a candle message
        if data.get("channel") == CHANNEL_NAME and "data" in data:
            candle_payload = data["data"]

            if isinstance(candle_payload, list) and len(candle_payload) >= 7:
                return [
                    CandleData(
                        timestamp_raw=self.ensure_timestamp_in_seconds(candle_payload[0]),
                        open=float(candle_payload[1]),
                        high=float(candle_payload[2]),
                        low=float(candle_payload[3]),
                        close=float(candle_payload[4]),
                        volume=float(candle_payload[5]),
                        quote_asset_volume=float(candle_payload[6]),
                        n_trades=0,  # Not provided by HyperLiquid
                        taker_buy_base_volume=0.0,  # Not provided
                        taker_buy_quote_volume=0.0,  # Not provided
                    )
                ]

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
