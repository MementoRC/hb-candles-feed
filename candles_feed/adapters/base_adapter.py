"""
Base adapter implementation for the Candle Feed V2 framework.

This module provides a base implementation for exchange adapters to reduce code duplication.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from decimal import Decimal

from candles_feed.core.candle_data import CandleData


class BaseAdapter(ABC):
    """Base class for exchange adapters.

    This abstract base class provides common functionality and defines the interface
    that all exchange adapters must implement.
    """

    TIMESTAMP_UNIT: str = ""

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

    @staticmethod
    @abstractmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :return: Trading pair in exchange-specific format
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

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param end_time: End time in seconds
        :param limit: Maximum number of candles to return
        :return: Dictionary of parameters for REST API request
        """
        pass

    @abstractmethod
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :return: WebSocket subscription payload
        """
        pass

    @abstractmethod
    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :return: List of CandleData objects
        """
        pass

    @abstractmethod
    def parse_ws_message(self, data: dict) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :return: List of CandleData objects or None if message is not a candle update
        """
        pass

    @abstractmethod
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :return: Dictionary mapping interval strings to their duration in seconds
        """
        pass

    @abstractmethod
    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :return: List of interval strings supported by WebSocket API
        """
        pass

    def convert_timestamp_to_exchange(self, timestamp: int | float | Decimal) -> int | str:
        """Convert seconds to exchange format based on TIMESTAMP_UNIT."""
        if self.TIMESTAMP_UNIT == "seconds":
            return int(timestamp)
        elif self.TIMESTAMP_UNIT == "milliseconds":
            return int(timestamp * 1000)
        elif self.TIMESTAMP_UNIT == "iso8601":
            return datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            raise NotImplementedError("Exchange must define TIMESTAMP_UNIT.")

    @staticmethod
    def ensure_timestamp_in_seconds(timestamp: int | float | str) -> int:
        """Convert exchange timestamp to internal seconds format."""
        if isinstance(timestamp, str) and ":" in timestamp:
            return int(datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp())

        timestamp = int(timestamp)
        if timestamp >= 1e18:  # Nanoseconds
            return int(timestamp / 1e9)
        elif timestamp >= 1e15:  # Microseconds
            return int(timestamp / 1e6)
        elif timestamp >= 1e12:  # Milliseconds
            return int(timestamp / 1e3)
        elif timestamp >= 1e9:  # Seconds
            return timestamp
        else:
            raise ValueError(
                f"Timestamp must be in iso, milli, micro, nano or seconds:{timestamp}"
            )

