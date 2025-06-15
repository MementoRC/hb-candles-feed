"""
Hybrid mock adapter implementing both sync and async patterns for testing.
"""

from typing import Any

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_config import NetworkConfig
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    DEFAULT_CANDLES_LIMIT,
    INTERVALS,
    REST_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)


@ExchangeRegistry.register("hybrid_mocked_adapter")
class HybridMockedAdapter(BaseAdapter):
    """
    Hybrid adapter that implements both sync and async patterns.

    This adapter is designed for testing both patterns with
    the candles feed framework.
    """

    TIMESTAMP_UNIT = "milliseconds"

    def __init__(self, *args, network_config: NetworkConfig | None = None, **kwargs):
        """Initialize the adapter.

        :param network_config: Network configuration for testnet/production
        :param args: Additional positional arguments
        :param kwargs: Additional keyword arguments, may include 'network_client'
        """
        super().__init__()  # Call object.__init__(), BaseAdapter has no __init__
        self._network_config: NetworkConfig | None = network_config
        self._network_client: NetworkClientProtocol | None = kwargs.get("network_client")

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert trading pair to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., BTC-USDT).
        :returns: Trading pair in exchange format (unchanged for simple mock).
        """
        # The mock exchange uses the same format (BTC-USDT)
        return trading_pair

    def get_supported_intervals(self) -> Dict[str, int]:
        """Get supported intervals and their duration in seconds.

        :returns: Dictionary mapping interval names to seconds.
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of supported interval strings.
        """
        return list(INTERVALS.keys())

    def get_ws_url(self) -> str:
        """Get the WebSocket API URL.

        :returns: WebSocket API URL.
        """
        return SPOT_WSS_URL

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> Dict[str, Any]:
        """Get WebSocket subscription payload.

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

    def parse_ws_message(self, message: dict[str, Any]) -> list[CandleData] | None:
        """Process WebSocket message into CandleData objects.

        :param message: WebSocket message.
        :returns: list of CandleData objects or None if the message doesn't contain candle data.
        """
        data = message.get("data", {})

        if not data or not data.get("timestamp"):
            return None

        timestamp = data.get("timestamp")
        # Convert timestamp to seconds
        timestamp = self.ensure_timestamp_in_seconds(timestamp)

        return [
            CandleData(
                timestamp_raw=timestamp,
                open=float(data.get("open", 0)),
                high=float(data.get("high", 0)),
                low=float(data.get("low", 0)),
                close=float(data.get("close", 0)),
                volume=float(data.get("volume", 0)),
                quote_asset_volume=float(data.get("quote_volume", 0)),
            )
        ]

    def _get_rest_url(self) -> str:  # type: ignore[override]
        """Get the REST API URL for candles.

        :returns: REST API URL.
        """
        return f"{SPOT_REST_URL}{REST_CANDLES_ENDPOINT}"

    def _get_rest_params(  # type: ignore[override]
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = DEFAULT_CANDLES_LIMIT,
    ) -> dict[str, Any]:
        """Get REST API request parameters.

        :param trading_pair: Trading pair in standard format.
        :param interval: Interval string.
        :param start_time: Start time in seconds.
        :param end_time: End time in seconds.
        :param limit: Maximum number of candles to retrieve.
        :returns: Dictionary of request parameters.
        """
        params: Dict[str, Any] = {
            "symbol": HybridMockedAdapter.get_trading_pair_format(trading_pair),
            "interval": interval,
            "limit": limit,
        }

        if start_time is not None:
            params["start_time"] = self.convert_timestamp_to_exchange(start_time)

        if end_time is not None:
            params["end_time"] = self.convert_timestamp_to_exchange(end_time)

        return params

    def _parse_rest_response(
        self, response_data: dict[Any, Any] | list[Any] | None
    ) -> list[CandleData]:
        """Process REST API response data into CandleData objects.

        :param response_data: Response data from the REST API.
        :returns: list of CandleData objects.
        """
        result: List[CandleData] = []

        # The mock server returns a standardized format
        if isinstance(response_data, dict) and response_data.get("status") == "ok":
            candles_payload = response_data.get("data", [])
            if not isinstance(candles_payload, list):  # Ensure candles_payload is a list
                return result  # Or handle error appropriately

            for candle_item in candles_payload:
                if not isinstance(candle_item, dict):
                    continue
                timestamp = candle_item.get("timestamp")

                # Convert timestamp to seconds
                timestamp = self.ensure_timestamp_in_seconds(timestamp)

                result.append(
                    CandleData(
                        timestamp_raw=timestamp,  # type: ignore
                        open=float(candle_item.get("open", 0)),
                        high=float(candle_item.get("high", 0)),
                        low=float(candle_item.get("low", 0)),
                        close=float(candle_item.get("close", 0)),
                        volume=float(candle_item.get("volume", 0)),
                        quote_asset_volume=float(candle_item.get("quote_volume", 0)),
                    )
                )

        return result

    def fetch_rest_candles_synchronous(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
    ) -> list[CandleData]:
        """Fetch candles using synchronous API calls.

        In a real implementation, this would make an HTTP request.
        For the mock adapter, we generate simulated candle data.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: List of CandleData objects
        """
        # Generate mock candle data
        current_time_sec: int = start_time or 1620000000  # Example timestamp
        interval_seconds: int = INTERVALS.get(interval, 60)

        # Handle None limit by using default value
        actual_limit = limit if limit is not None else 500

        candle_payloads: List[Dict[str, Any]] = []
        for i in range(actual_limit):
            timestamp_sec: int = current_time_sec + (i * interval_seconds)
            candle_payloads.append(
                {
                    "timestamp": timestamp_sec * 1000,  # Convert to milliseconds
                    "open": 100.0 + i,
                    "high": 101.0 + i,
                    "low": 99.0 + i,
                    "close": 100.5 + i,
                    "volume": 1000.0 + i * 10,
                    "quote_volume": 100500.0 + i * 100,
                }
            )

        # Create a response like what our mock server would return
        response_payload: Dict[str, Any] = {"status": "ok", "data": candle_payloads}

        return self._parse_rest_response(response_payload)

    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles using asynchronous API calls.

        Unlike the SyncOnlyAdapter or AsyncOnlyAdapter, this implementation
        has custom implementations for both sync and async methods.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :param network_client: Optional network client to use
        :returns: List of CandleData objects
        """
        # Use the provided client, the instance client, or simulate one
        client: Optional[NetworkClientProtocol] = network_client or self._network_client
        if client:
            # In a real implementation, we'd use the client to make a request
            # For the mock adapter, we'll just generate test data with
            # a slightly different pattern than the sync method
            # This is a mock, so we don't actually use the client here.
            pass

        # Generate different mock candle data for async to demonstrate
        # that this is actually using the async implementation
        current_time_sec: int = start_time or 1620000000  # Example timestamp
        interval_seconds: int = INTERVALS.get(interval, 60)

        # Handle None limit by using default value
        actual_limit = limit if limit is not None else 500

        candle_payloads: List[Dict[str, Any]] = []
        for i in range(actual_limit):
            timestamp_sec: int = current_time_sec + (i * interval_seconds)
            # Different price pattern to distinguish from sync method
            candle_payloads.append(
                {
                    "timestamp": timestamp_sec * 1000,  # Convert to milliseconds
                    "open": 200.0 + i * 2,
                    "high": 205.0 + i * 2,
                    "low": 195.0 + i * 2,
                    "close": 202.5 + i * 2,
                    "volume": 2000.0 + i * 20,
                    "quote_volume": 405000.0 + i * 200,
                }
            )

        # Create a response like what our mock server would return
        response_payload: Dict[str, Any] = {"status": "ok", "data": candle_payloads}

        return self._parse_rest_response(response_payload)
