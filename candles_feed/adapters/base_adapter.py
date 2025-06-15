"""
Base adapter implementation for the Candle Feed framework.

This module provides a base implementation for exchange adapters to reduce code duplication.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict # Added Any, Dict

from candles_feed.core.candle_data import CandleData


class BaseAdapter(ABC):
    """Base class for exchange adapters with common functionality.

    This abstract base class provides timestamp handling utilities and defines
    the required interface methods for all exchange adapters.
    """

    # Common timestamp handling
    TIMESTAMP_UNIT: str = ""

    @staticmethod
    @abstractmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in exchange-specific format
        """
        pass

    @abstractmethod
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        pass

    @abstractmethod
    def get_ws_url(self) -> str:
        """Get WebSocket URL for the exchange.

        :returns: WebSocket URL
        :raises NotImplementedError: If WebSocket is not supported
        """
        pass

    @abstractmethod
    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        :raises NotImplementedError: If WebSocket is not supported
        """
        pass

    @abstractmethod
    def parse_ws_message(self, data: Dict[str, Any]) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        :raises NotImplementedError: If WebSocket is not supported
        """
        pass

    @abstractmethod
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :returns: WebSocket subscription payload
        :raises NotImplementedError: If WebSocket is not supported
        """
        pass

    # Private implementation methods for subclasses
    @abstractmethod
    def _get_rest_url(self) -> str:
        """Internal method to get REST API URL.

        Subclasses must implement this to provide the base REST API URL for candles.
        This method is an instance method to allow for dynamic URL construction
        if needed (e.g., based on `self`'s configuration).

        :returns: REST API URL
        """
        pass

    @abstractmethod
    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,  # Default matches AdapterProtocol.fetch_rest_candles
    ) -> dict:
        """Internal method to get parameters for REST API request.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: Dictionary of parameters for REST API request
        """
        raise NotImplementedError("Subclasses must implement _get_rest_params")

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Internal method to parse REST API response.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        raise NotImplementedError("Subclasses must implement _parse_rest_response")

    def convert_timestamp_to_exchange(self, timestamp: int | float | Decimal) -> int | str:
        """Convert timestamp from seconds to exchange timestamp format.

        :param timestamp: Timestamp in seconds
        :returns: Timestamp in exchange format
        :raises NotImplementedError: If TIMESTAMP_UNIT is not defined
        """
        if self.TIMESTAMP_UNIT == "seconds":
            return int(timestamp)
        if self.TIMESTAMP_UNIT.lower() == "milliseconds":
            return int(timestamp * 1000)
        if self.TIMESTAMP_UNIT == "iso8601":
            return datetime.fromtimestamp(float(timestamp), timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        raise NotImplementedError("Exchange must define TIMESTAMP_UNIT.")

    @staticmethod
    def ensure_timestamp_in_seconds(timestamp: int | str | float | None) -> int:
        """Ensure timestamp is in seconds.

        :param timestamp: Timestamp in exchange format or None
        :returns: Timestamp in seconds, current time if None is provided
        :raises ValueError: If timestamp is not in a recognized format
        """
        if timestamp is None:
            # Return current time in seconds if None is provided
            return int(datetime.now(timezone.utc).timestamp())

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
            raise ValueError(f"Timestamp must be in iso, milli, micro, nano or seconds:{timestamp}")
