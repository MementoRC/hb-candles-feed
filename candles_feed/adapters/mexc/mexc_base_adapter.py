"""
Base MEXC adapter implementation for the Candle Feed framework.

This module provides a base implementation for MEXC-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod
from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.mexc.constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SUB_ENDPOINT_NAME,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData


class MEXCBaseAdapter(BaseAdapter):
    """Base class for MEXC exchange adapters.

    This class provides shared functionality for MEXC spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")

        Returns:
            Trading pair in MEXC format (e.g., "BTC_USDT")
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
    def get_kline_topic(self) -> str:
        """Get WebSocket kline topic prefix.

        Returns:
            Kline topic prefix string
        """
        pass

    @abstractmethod
    def get_interval_format(self, interval: str) -> str:
        """Get exchange-specific interval format.

        Args:
            interval: Standard interval format

        Returns:
            Exchange-specific interval format
        """
        pass

    @abstractmethod
    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
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
        pass

    @abstractmethod
    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        pass

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        Args:
            trading_pair: Trading pair
            interval: Candle interval

        Returns:
            WebSocket subscription payload
        """
        # Prepare the symbol in MEXC format
        symbol = self.get_trading_pair_format(trading_pair).replace("_", "").lower()
        mexc_interval = self.get_interval_format(interval)

        return {
            "method": SUB_ENDPOINT_NAME,
            "params": [f"{self.get_kline_topic()}{mexc_interval}_{symbol}"],
        }

    @abstractmethod
    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        pass

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        Returns:
            Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        Returns:
            List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS
