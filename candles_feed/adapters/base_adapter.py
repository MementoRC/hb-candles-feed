"""
Base adapter implementation for the Candle Feed V2 framework.

This module provides a base implementation for exchange adapters to reduce code duplication.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from candles_feed.core.candle_data import CandleData


class BaseAdapter(ABC):
    """Base class for exchange adapters.

    This abstract base class provides common functionality and defines the interface
    that all exchange adapters must implement.
    """

    @abstractmethod
    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")

        Returns:
            Trading pair in exchange-specific format
        """
        pass

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
    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> dict[str, str | int]:
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

    @abstractmethod
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        Args:
            trading_pair: Trading pair
            interval: Candle interval

        Returns:
            WebSocket subscription payload
        """
        pass

    @abstractmethod
    def parse_ws_message(self, data: dict) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        pass

    @abstractmethod
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        Returns:
            Dictionary mapping interval strings to their duration in seconds
        """
        pass

    @abstractmethod
    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        Returns:
            List of interval strings supported by WebSocket API
        """
        pass
