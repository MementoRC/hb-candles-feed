"""
Mock implementations of Hummingbot components for testing.

This module provides mock implementations of Hummingbot's networking components
that can be used for testing without actual dependencies on Hummingbot.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any

# Define mock classes that mimic Hummingbot's interfaces


@dataclass
class WSResponse:
    """Mock WebSocket response for testing."""

    data: Any


class MockAsyncThrottler:
    """Mock implementation of AsyncThrottlerBase."""

    def __init__(self, rate_limits: list[dict[str, Any]] | None = None):
        """Initialize the mock throttler.

        :param rate_limits: list of rate limit dictionaries.
        """
        self.rate_limits: list[dict[str, Any]] = rate_limits or []
        self.task_logs: list[tuple[str, float]] = []

    async def execute_task(self, limit_id: str):
        """Execute a task respecting rate limits.

        This is a context manager that simulates rate limiting.

        :param limit_id: The rate limit identifier.
        """
        # Create a context manager instance with access to self
        throttler_instance = self

        class MockContext:
            async def __aenter__(self):
                # Log the task for testing assertions
                throttler_instance.task_logs.append((limit_id, asyncio.get_event_loop().time()))
                return None

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        return MockContext()


class MockRESTConnection:
    """Mock REST connection for testing."""

    def __init__(self, responses: dict[str, Any] | None = None):
        """Initialize the mock connection.

        :param responses: dictionary mapping URLs to mock responses.
        """
        self.responses: dict[str, Any] = responses or {}
        self.requests: list[dict[str, Any]] = []

    async def call(
        self,
        url: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Make a mock REST call.

        :param url: URL to call.
        :param method: HTTP method.
        :param params: Query parameters.
        :param data: Request data.
        :param headers: Request headers.
        :returns: Mock response for the given URL.
        """
        # Record the request for testing assertions
        self.requests.append(  # type: ignore
            {  # type: ignore
                "url": url,  # type: ignore
                "method": method,  # type: ignore
                "params": params,  # type: ignore
                "data": data,  # type: ignore
                "headers": headers,  # type: ignore
            }
        )

        # Return the pre-configured response for this URL if available
        if url not in self.responses:
            raise ValueError(f"No mock response configured for URL: {url}")

        response_data_val: Dict[str, Any] = self.responses[url]

        # Create a mock response object
        class MockResponse:
            async def json(self) -> Dict[str, Any]:
                return response_data_val

            status: int = 200

        return MockResponse()


class MockWSConnection:
    """Mock WebSocket connection for testing."""

    def __init__(self, messages: list[Any] | None = None):
        """Initialize the mock connection.

        :param messages: list of messages to return when iterating.
        """
        self.messages: list[Any] = messages or []
        self.sent_messages: list[Any] = []
        self.connected: bool = False
        self.url: str | None = None

    async def connect(self, ws_url: str):
        """Connect to a WebSocket.

        :param ws_url: WebSocket URL.
        """
        self.url = ws_url
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        self.connected = False

    async def send(self, message: Any) -> None:
        """Send a message over WebSocket.

        :param message: Message to send.
        """
        if isinstance(message, str):
            try:
                parsed = json.loads(message)
                self.sent_messages.append(parsed)
            except json.JSONDecodeError:
                self.sent_messages.append(message)
        else:
            self.sent_messages.append(message)

    async def iter_messages(self):
        """Iterate over mock messages.

        :yields: Mock WebSocket responses.
        """
        for message in self.messages:
            yield WSResponse(data=message)


class MockRESTAssistant:
    """Mock REST assistant for testing."""

    def __init__(self, connection: MockRESTConnection):
        """Initialize the mock assistant.

        :param connection: Mock REST connection.
        """
        self.connection: MockRESTConnection = connection

    async def call(
        self,
        url: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Make a mock REST call.

        :param url: URL to call.
        :param method: HTTP method.
        :param params: Query parameters.
        :param data: Request data.
        :param headers: Request headers.
        :returns: Mock response for the given URL.
        """
        return await self.connection.call(url, method, params, data, headers)


class MockWSAssistant:
    """Mock WebSocket assistant for testing."""

    def __init__(self, connection: MockWSConnection):
        """Initialize the mock assistant.

        :param connection: Mock WebSocket connection.
        """
        self.connection: MockWSConnection = connection

    async def connect(self, ws_url: str) -> None:
        """Connect to a WebSocket.

        :param ws_url: WebSocket URL.
        """
        await self.connection.connect(ws_url)

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        await self.connection.disconnect()

    async def send(self, message: Any) -> None:
        """Send a message over WebSocket.

        :param message: Message to send.
        """
        await self.connection.send(message)

    async def iter_messages(self):
        """Iterate over mock messages.

        :yields: Mock WebSocket responses.
        """
        async for message in self.connection.iter_messages():
            yield message


class MockWebAssistantsFactory:
    """Mock WebAssistantsFactory for testing."""

    def __init__(
        self,
        throttler: MockAsyncThrottler | None = None,
        rest_responses: dict[str, Any] | None = None,
        ws_messages: list[Any] | None = None,
    ):
        """Initialize the mock factory.

        :param throttler: Mock throttler.
        :param rest_responses: dictionary mapping URLs to mock responses.
        :param ws_messages: list of messages to return when iterating.
        """
        self.throttler: MockAsyncThrottler = throttler or MockAsyncThrottler()
        self.rest_connection: MockRESTConnection = MockRESTConnection(rest_responses)
        self.ws_connection: MockWSConnection = MockWSConnection(ws_messages)

    async def get_rest_assistant(self) -> MockRESTAssistant:
        """Get a mock REST assistant.

        :returns: Mock REST assistant.
        """
        return MockRESTAssistant(self.rest_connection)

    async def get_ws_assistant(self) -> MockWSAssistant:
        """Get a mock WebSocket assistant.

        :returns: Mock WebSocket assistant.
        """
        return MockWSAssistant(self.ws_connection)

    async def close(self) -> None:
        """Close the factory and all connections."""
        if self.ws_connection.connected:
            await self.ws_connection.disconnect()

    async def __aenter__(self) -> "MockWebAssistantsFactory":
        """Enter async context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """Exit async context."""
        await self.close()


def create_mock_hummingbot_components(rest_responses=None, ws_messages=None, rate_limits=None):
    """Create mock Hummingbot components for testing.

    :param rest_responses: Dictionary mapping URLs to mock responses.
    :param ws_messages: List of messages to return when iterating.
    :param rate_limits: List of rate limit dictionaries.
    :returns: Dictionary containing mock components:
        - throttler: MockAsyncThrottler instance
        - web_assistants_factory: MockWebAssistantsFactory instance.
    """
    throttler_instance: MockAsyncThrottler = MockAsyncThrottler(rate_limits)
    web_assistants_factory_instance: MockWebAssistantsFactory = MockWebAssistantsFactory(
        throttler=throttler_instance, rest_responses=rest_responses, ws_messages=ws_messages
    )

    return {
        "throttler": throttler_instance,
        "web_assistants_factory": web_assistants_factory_instance,
    }
