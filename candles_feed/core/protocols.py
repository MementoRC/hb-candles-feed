"""
Protocol definitions for the Candle Feed framework.

This module defines the core interface contracts for the framework
using Python's typing.Protocol system.
"""

from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol, runtime_checkable

from candles_feed.core.candle_data import CandleData


@runtime_checkable
class WSAssistant(Protocol):
    """Protocol for WebSocket assistants."""

    async def connect(self) -> None:
        """Connect to WebSocket."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        ...

    async def send(self, payload: Any) -> None:
        """Send request to WebSocket.

        :param payload: Message payload to send
        """
        ...

    def iter_messages(self) -> AsyncGenerator[Any, None]:
        """Iterate over WebSocket messages.

        :returns: AsyncGenerator yielding WebSocket messages
        """
        ...


@runtime_checkable
class CollectionStrategy(Protocol):
    """Protocol for strategies that collect candle data.

    This protocol defines the interface for different data collection strategies,
    such as WebSocket streaming or REST API polling.
    """

    async def poll_once(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> list[CandleData]:
        """Fetch candles for a specific time range.

        :param start_time: Start time in seconds
        :param end_time: End time in seconds
        :param limit: Maximum number of candles to return
        :returns: List of CandleData objects
        """
        ...

    async def start(self) -> None:
        """Start the collection strategy.

        Initiates data collection according to the strategy's approach.
        """
        ...

    async def stop(self) -> None:
        """Stop the collection strategy.

        Stops data collection and cleans up any resources.
        """
        ...


class Logger(Protocol):
    """Protocol for loggers."""

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log debug message."""
        ...

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log info message."""
        ...

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log warning message."""
        ...

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log error message."""
        ...

    def exception(self, msg: str, *args, **kwargs) -> None:
        """Log exception message."""
        ...


@runtime_checkable
class NetworkClientProtocol(Protocol):
    """Protocol defining the network client interface.

    This protocol abstracts the network communication layer,
    allowing for different implementations (standalone, Hummingbot-based, etc.)
    """

    async def get_rest_data(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        method: str = "GET",
    ) -> Any:
        """Get data from REST API.

        :param url: REST API URL
        :param params: Query parameters
        :param data: Request body data
        :param headers: Request headers
        :param method: HTTP method
        :return: REST API response
        """
        ...

    async def establish_ws_connection(self, url: str) -> WSAssistant:
        """Establish a websocket connection.

        :param url: WebSocket URL
        :return: WSAssistant instance
        """
        ...

    async def send_ws_message(self, ws_assistant: WSAssistant, payload: dict[str, Any]) -> None:
        """Send a message over WebSocket.

        :param ws_assistant: WebSocket assistant
        :param payload: Message payload
        """
        ...

    async def close(self) -> None:
        """Close the client, cleaning up any resources."""
        ...

    async def __aenter__(self) -> "NetworkClientProtocol":
        """Allow usage as an async context manager."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager."""
        ...


@runtime_checkable
class AsyncThrottlerProtocol(Protocol):
    """Protocol for API rate limiters.

    This protocol abstracts the rate limiting functionality,
    allowing for different implementations.
    """

    def execute_task(self, limit_id: str) -> AbstractAsyncContextManager[Any]:
        """Return an async context manager that throttles the enclosed task.

        Mirrors hummingbot's ``AsyncThrottlerBase.execute_task``: a plain (non-async)
        method used as ``async with throttler.execute_task(limit_id): ...``. Entering
        the context waits until the limit (and any linked limits) have capacity.

        :param limit_id: The rate limit identifier
        :returns: Async context manager guarding the task
        """
        ...


@runtime_checkable
class RestRateLimiterProtocol(Protocol):
    """Protocol for the limiter that paces REST requests of one feed.

    ``AsyncRateLimiter`` satisfies it; so does the hummingbot connector bridge that
    draws from the host connector's shared budget.
    """

    async def acquire(self) -> None:
        """Wait until one REST request may be sent, then record it."""
        ...
