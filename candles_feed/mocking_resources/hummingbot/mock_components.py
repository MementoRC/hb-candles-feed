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

    def add_rate_limits(self, rate_limits: list[Any]) -> None:
        """Record added rate limits (additive; ids already present are skipped).

        :param rate_limits: Rate limit objects with a ``limit_id`` attribute.
        """
        known = {r["limit_id"] if isinstance(r, dict) else r.limit_id for r in self.rate_limits}
        for rate_limit in rate_limits:
            if rate_limit.limit_id not in known:
                self.rate_limits.append(rate_limit)
                known.add(rate_limit.limit_id)

    def execute_task(self, limit_id: str):
        """Return an async context manager simulating rate limiting.

        Synchronous like upstream ``AsyncThrottlerBase.execute_task``.

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
        self.errors: dict[str, tuple[int, dict[str, str]]] = {}

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

        response_data_val: dict[str, Any] = self.responses[url]
        response_status, response_headers = self.errors.get(url, (200, {}))

        # Create a mock response object
        class MockResponse:
            async def json(self) -> dict[str, Any]:
                return response_data_val

            async def text(self) -> str:
                return json.dumps(response_data_val)

            status: int = response_status
            headers: dict[str, str] = response_headers

        return MockResponse()

    def set_error(self, url: str, status: int, headers: dict[str, str] | None = None) -> None:
        """Make calls to ``url`` answer ``status`` (with ``headers``) instead of 200.

        :param url: URL to fail (must also have a configured response body).
        :param status: HTTP status to answer.
        :param headers: Response headers, e.g. ``{"Retry-After": "7"}``.
        """
        self.errors[url] = (status, headers or {})


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

    async def call(self, request: Any, timeout: float | None = None):
        """Make a mock REST call, shaped like upstream ``RESTAssistant.call``.

        :param request: A RESTRequest-like object (``url``, ``method``, ``params``,
            ``data``, ``headers``).
        :param timeout: Ignored.
        :returns: Mock response for the request's URL.
        """
        method = getattr(request.method, "name", request.method)
        return await self.connection.call(
            request.url, method, request.params, request.data, request.headers
        )


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


@dataclass
class MockRESTRequest:
    """Duck-typed stand-in for hummingbot's ``RESTRequest`` (``method`` is a plain string)."""

    method: str
    url: str | None = None
    params: Any = None
    data: Any = None
    headers: Any = None


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
        # Used by HummingbotNetworkClient when hummingbot's RESTRequest is not importable.
        self.rest_request_class: type[MockRESTRequest] = MockRESTRequest
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
