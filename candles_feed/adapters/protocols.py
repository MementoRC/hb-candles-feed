from typing import TYPE_CHECKING, Any, Optional, Protocol, TypeVar, runtime_checkable

from candles_feed.core.candle_data import CandleData

if TYPE_CHECKING:
    from candles_feed.core.protocols import NetworkClientProtocol


NetworkClientProtocolT = TypeVar("NetworkClientProtocolT", bound="NetworkClientProtocol | None")


@runtime_checkable
class AdapterProtocol(Protocol):
    """Protocol for exchange adapters.

    This protocol defines the interface that all exchange adapters must implement.
    Adapters can choose to implement either synchronous or asynchronous REST methods
    (or both), but must implement the required WebSocket methods if WebSocket
    functionality is needed.
    """

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in exchange-specific format
        """
        ...

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        ...

    def get_ws_url(self) -> str:
        """Get WebSocket URL for the exchange.

        :returns: WebSocket URL
        :raises NotImplementedError: If WebSocket is not supported
        """
        ...

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        :raises NotImplementedError: If WebSocket is not supported
        """
        ...

    def parse_ws_message(self, data: Any) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        :raises NotImplementedError: If WebSocket is not supported
        """
        ...

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :returns: WebSocket subscription payload
        :raises NotImplementedError: If WebSocket is not supported
        """
        ...

    # One or both of these methods must be implemented:
    def fetch_rest_candles_synchronous(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
    ) -> list[CandleData]:
        """Fetch candles using synchronous API calls.

        Implement this method for adapters that use synchronous HTTP clients.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: List of CandleData objects
        :raises NotImplementedError: If the adapter only supports async operations
        """
        ...

    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
        network_client: NetworkClientProtocolT | None = None,
    ) -> list[CandleData]:
        """Fetch candles using asynchronous API calls.

        Implement this method for adapters that use asynchronous HTTP clients.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :param network_client: Optional network client to use for requests
        :returns: List of CandleData objects
        :raises NotImplementedError: If the adapter only supports sync operations
        """
        ...
