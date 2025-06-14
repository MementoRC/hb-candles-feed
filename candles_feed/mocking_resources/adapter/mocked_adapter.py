"""
Simple mock adapter for testing the candles feed framework.
"""

from typing import Any, Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_config import NetworkConfig

from .constants import (
    DEFAULT_CANDLES_LIMIT,
    INTERVALS,
    REST_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)


@ExchangeRegistry.register("mocked_adapter")
class MockedAdapter(BaseAdapter):
    """
    Adapter for the simple mock exchange REST and WebSocket APIs.

    This adapter is designed for testing the candles feed framework.
    It provides a simplified, standardized interface that's focused on
    testing rather than mimicking a real exchange.
    """

    def __init__(self, *args, network_config: Optional[NetworkConfig] = None, **kwargs):
        """Initialize the adapter.

        :param network_config: Network configuration for testnet/production
        :param args: Additional positional arguments
        :param kwargs: Additional keyword arguments, may include 'network_client'
        """
        super().__init__()  # Call object.__init__()
        self._network_config = network_config
        self._network_client = kwargs.get("network_client")

    def get_intervals(self) -> Dict[str, int]:
        """
        Get supported intervals and their duration in seconds.

        :returns: Dictionary mapping interval names to seconds.
        """
        return INTERVALS

    def get_supported_intervals(self) -> Dict[str, int]:
        """
        Get supported intervals and their duration in seconds.

        :returns: Dictionary mapping interval names to seconds.
        """
        return self.get_intervals()

    def get_ws_supported_intervals(self) -> List[str]:
        """
        Get intervals supported by WebSocket API.

        :returns: List of supported interval strings.
        """
        return list(INTERVALS.keys())

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """
        Convert trading pair to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., BTC-USDT).
        :returns: Trading pair in exchange format (unchanged for simple mock).
        """
        # The mock exchange uses the same format (BTC-USDT)
        return trading_pair

    def get_rest_url(self) -> str:
        """
        Get the REST API URL for candles.

        :returns: REST API URL.
        """
        return f"{SPOT_REST_URL}{REST_CANDLES_ENDPOINT}"

    def get_ws_url(self) -> str:
        """
        Get the WebSocket API URL.

        :returns: WebSocket API URL.
        """
        return SPOT_WSS_URL

    def _get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :return: REST API URL
        """
        return f"{SPOT_REST_URL}{REST_CANDLES_ENDPOINT}"

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: Optional[int] = None,
        limit: int = DEFAULT_CANDLES_LIMIT,
    ) -> Dict[str, Any]:
        """Get REST API request parameters.

        :param trading_pair: Trading pair in standard format
        :param interval: Interval string
        :param start_time: Start time in milliseconds
        :param limit: Maximum number of candles to retrieve
        :return: Dictionary of request parameters
        """
        return self.get_rest_params(trading_pair, interval, limit, start_time)

    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        limit: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get REST API request parameters.

        :param trading_pair: Trading pair in standard format.
        :param interval: Interval string.
        :param limit: Maximum number of candles to retrieve.
        :param start_time: Start time in milliseconds.
        :param end_time: End time in milliseconds.
        :returns: Dictionary of request parameters.
        """
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": interval,
            "limit": limit if limit is not None else DEFAULT_CANDLES_LIMIT,
        }

        if start_time is not None:
            params["start_time"] = start_time

        if end_time is not None:
            params["end_time"] = end_time

        return params

    def parse_rest_response(
        self,
        response_data: Dict[str, Any],
        trading_pair: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> List[CandleData]:
        """Alias for process_rest_response to match BaseAdapter interface.

        Note: This method makes trading_pair and interval optional to support the
        CandlesFeed which calls this method without providing those parameters.
        It extracts them from the response data instead.
        """
        if trading_pair is None and "symbol" in response_data:
            trading_pair = response_data["symbol"]

        if interval is None and "interval" in response_data:
            interval = response_data["interval"]

        return self.process_rest_response(response_data, trading_pair, interval)

    def _parse_rest_response(self, data: Dict[str, Any] | List[Any] | None) -> List[CandleData]:
        """Parse REST API response data into CandleData objects.

        :param data: Response data from the REST API
        :return: List of CandleData objects
        """
        if not isinstance(data, dict):  # Handles None and list cases
            return []

        # Delegate to existing parse_rest_response method, data is now known to be a dict
        return self.parse_rest_response(data)

    def process_rest_response(
        self, response_data: Dict[str, Any], trading_pair: Optional[str], interval: Optional[str]
    ) -> List[CandleData]:
        """
        Process REST API response data into CandleData objects.

        :param response_data: Response data from the REST API.
        :param trading_pair: Trading pair in standard format.
        :param interval: Interval string.
        :returns: List of CandleData objects.
        """
        result = []

        # The mock server returns a standardized format
        if "status" in response_data and response_data["status"] == "ok":
            candles_data = response_data.get("data", [])

            for candle in candles_data:
                timestamp = candle.get("timestamp")

                # Convert timestamp to seconds if it's in milliseconds
                if timestamp > 10000000000:  # Heuristic to detect milliseconds
                    timestamp = timestamp // 1000

                result.append(
                    CandleData(
                        timestamp_raw=timestamp,
                        open=float(candle.get("open")),
                        high=float(candle.get("high")),
                        low=float(candle.get("low")),
                        close=float(candle.get("close")),
                        volume=float(candle.get("volume")),
                        quote_asset_volume=float(candle.get("quote_volume", 0)),
                    )
                )

        return result

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> Dict[str, Any]:
        """
        Get WebSocket subscription payload.

        :param trading_pair: Trading pair in standard format.
        :param interval: Interval string.
        :returns: Subscription payload.
        """
        return {
            "type": "subscribe",
            "subscriptions": [
                {"symbol": self.get_trading_pair_format(trading_pair), "interval": interval}
            ],
        }

    def parse_ws_message(self, data: dict[str, Any]) -> list[CandleData] | None:
        """Alias for process_ws_message to match BaseAdapter interface."""
        return self.process_ws_message(data)

    def process_ws_message(self, message: dict[str, Any]) -> list[CandleData] | None:
        """
        Process WebSocket message into CandleData object.

        :param message: WebSocket message.
        :returns: CandleData object or None if the message doesn't contain candle data.
        """
        data = message.get("data", {})

        timestamp = data.get("timestamp")
        # Convert timestamp to seconds if it's in milliseconds
        if timestamp and timestamp > 10000000000:  # Heuristic to detect milliseconds
            timestamp = timestamp // 1000

        return [
            CandleData(
                timestamp_raw=timestamp,
                open=float(data.get("open")),
                high=float(data.get("high")),
                low=float(data.get("low")),
                close=float(data.get("close")),
                volume=float(data.get("volume")),
                quote_asset_volume=float(data.get("quote_volume", 0)),
            )
        ]
