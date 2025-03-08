"""
Mock implementations of Hummingbot components for testing.

This module provides mock implementations of Hummingbot's networking components
that can be used for testing without actual dependencies on Hummingbot.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List

# Define mock classes that mimic Hummingbot's interfaces


@dataclass
class WSResponse:
    """Mock WebSocket response for testing."""

    data: Any


class MockAsyncThrottler:
    """Mock implementation of AsyncThrottlerBase."""

    def __init__(self, rate_limits: List[Dict[str, Any]] = None):
        """Initialize the mock throttler.

        :param rate_limits: List of rate limit dictionaries.
        """
        self.rate_limits = rate_limits or []
        self.task_logs = []

    async def execute_task(self, limit_id: str):
        """Execute a task respecting rate limits.

        This is a context manager that simulates rate limiting.

        :param limit_id: The rate limit identifier.
        """

        # Just a pass-through context manager for testing
        class MockContext:
            async def __aenter__(self):
                # Log the task for testing assertions
                self.task_logs.append((limit_id, asyncio.get_event_loop().time()))
                return None

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        return MockContext()


class MockRESTConnection:
    """Mock REST connection for testing."""

    def __init__(self, responses=None):
        """Initialize the mock connection.

        :param responses: Dictionary mapping URLs to mock responses.
        """
        self.responses = responses or {}
        self.requests = []

    async def call(self, url, method="GET", params=None, data=None, headers=None):
        """Make a mock REST call.

        :param url: URL to call.
        :param method: HTTP method.
        :param params: Query parameters.
        :param data: Request data.
        :param headers: Request headers.
        :returns: Mock response for the given URL.
        """
        # Record the request for testing assertions
        self.requests.append(
            {
                "url": url,
                "method": method,
                "params": params,
                "data": data,
                "headers": headers,
            }
        )

        # Return the pre-configured response for this URL if available
        response_data = self.responses.get(url, {"status": "ok"})

        # Create a mock response object
        class MockResponse:
            async def json(self):
                return response_data

            status = 200

        return MockResponse()


class MockWSConnection:
    """Mock WebSocket connection for testing."""

    def __init__(self, messages=None):
        """Initialize the mock connection.

        :param messages: List of messages to return when iterating.
        """
        self.messages = messages or []
        self.sent_messages = []
        self.connected = False
        self.url = None

    async def connect(self, ws_url):
        """Connect to a WebSocket.

        :param ws_url: WebSocket URL.
        """
        self.url = ws_url
        self.connected = True

    async def disconnect(self):
        """Disconnect from WebSocket."""
        self.connected = False

    async def send(self, message):
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
        self.connection = connection

    async def call(self, url, method="GET", params=None, data=None, headers=None):
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
        self.connection = connection

    async def connect(self, ws_url):
        """Connect to a WebSocket.

        :param ws_url: WebSocket URL.
        """
        await self.connection.connect(ws_url)

    async def disconnect(self):
        """Disconnect from WebSocket."""
        await self.connection.disconnect()

    async def send(self, message):
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

    def __init__(self, throttler=None, rest_responses=None, ws_messages=None):
        """Initialize the mock factory.

        :param throttler: Mock throttler.
        :param rest_responses: Dictionary mapping URLs to mock responses.
        :param ws_messages: List of messages to return when iterating.
        """
        self.throttler = throttler or MockAsyncThrottler()
        self.rest_connection = MockRESTConnection(rest_responses)
        self.ws_connection = MockWSConnection(ws_messages)

    async def get_rest_assistant(self):
        """Get a mock REST assistant.

        :returns: Mock REST assistant.
        """
        return MockRESTAssistant(self.rest_connection)

    async def get_ws_assistant(self):
        """Get a mock WebSocket assistant.

        :returns: Mock WebSocket assistant.
        """
        return MockWSAssistant(self.ws_connection)

    async def close(self):
        """Close the factory and all connections."""
        if self.ws_connection.connected:
            await self.ws_connection.disconnect()

    async def __aenter__(self):
        """Enter async context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
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
    throttler = MockAsyncThrottler(rate_limits)
    web_assistants_factory = MockWebAssistantsFactory(
        throttler=throttler, rest_responses=rest_responses, ws_messages=ws_messages
    )

    return {"throttler": throttler, "web_assistants_factory": web_assistants_factory}
