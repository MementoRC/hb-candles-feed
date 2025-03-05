"""
Adapter for Hummingbot's network components.

This module provides adapters that allow the Candle Feed framework to use
Hummingbot's WebAssistantsFactory and AsyncThrottler when available.
"""

import json
import logging
from typing import Any, AsyncContextManager, Optional, cast

from candles_feed.core.protocols import (
    AsyncThrottlerProtocol,
    Logger,
    NetworkClientProtocol,
    WSAssistant,
)

# These imports use type-checking guard to avoid direct dependency
# They will only be imported at runtime if the components are available
try:
    from hummingbot.core.api_throttler.async_throttler_base import AsyncThrottlerBase
    from hummingbot.core.web_assistant.rest_assistant import RESTAssistant
    from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
    from hummingbot.core.web_assistant.ws_assistant import WSAssistant as HummingbotWSAssistant

    HUMMINGBOT_AVAILABLE = True
except ImportError:
    # Define placeholder types for type checking
    from typing import Any

    WebAssistantsFactory = Any
    RESTAssistant = Any
    HummingbotWSAssistant = Any
    AsyncThrottlerBase = Any
    HUMMINGBOT_AVAILABLE = False


class HummingbotWSAssistantAdapter(WSAssistant):
    """Adapter for Hummingbot's WSAssistant to match our WSAssistant protocol."""

    def __init__(self, ws_assistant, logger: Optional[Logger] = None):
        """Initialize the adapter.

        :param ws_assistant: Hummingbot's WSAssistant instance
        :param logger: Logger instance
        """
        self._ws = ws_assistant
        self._logger = logger or logging.getLogger(__name__)

    async def connect(self) -> None:
        """Connect to WebSocket."""
        # Hummingbot's WSAssistant is already connected in the factory
        pass

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        if hasattr(self._ws, "disconnect"):
            await self._ws.disconnect()

    async def send(self, payload: Any) -> None:
        """Send a message over WebSocket.

        :param payload: Message payload
        """
        if isinstance(payload, dict):
            await self._ws.send(json.dumps(payload))
        else:
            await self._ws.send(payload)

    async def iter_messages(self):
        """Iterate through incoming messages.

        Yields:
            WebSocket messages
        """
        try:
            # Adapt the Hummingbot WSAssistant message format to our expected format
            async for ws_response in self._ws.iter_messages():
                if ws_response.data:
                    try:
                        if isinstance(ws_response.data, str):
                            yield json.loads(ws_response.data)
                        else:
                            yield ws_response.data
                    except json.JSONDecodeError:
                        self._logger.error(f"Failed to parse WebSocket message: {ws_response.data}")
        except Exception as e:
            self._logger.error(f"Error iterating WebSocket messages: {e}")
            raise

    def __aiter__(self):
        """Return self as an async iterator."""
        return self.iter_messages()


class HummingbotThrottlerAdapter(AsyncThrottlerProtocol):
    """Adapter for Hummingbot's AsyncThrottler to match our AsyncThrottlerProtocol."""

    def __init__(self, throttler: AsyncThrottlerBase):
        """Initialize the adapter.

        :param throttler: Hummingbot's AsyncThrottler instance
        """
        self._throttler = throttler

    async def execute_task(self, limit_id: str, weight: int = 1) -> None:
        """Execute a task respecting rate limits.

        :param limit_id: The rate limit identifier
        :param weight: The weight of the task (default: 1)
        """
        async with self._throttler.execute_task(limit_id=limit_id):
            pass  # The context manager handles the rate limiting


class HummingbotNetworkClient(NetworkClientProtocol):
    """Network client that uses Hummingbot's web assistants for communication.

    This class adapts Hummingbot's web assistants to work with our NetworkClientProtocol,
    allowing the Candle Feed framework to use Hummingbot's networking components when available.
    """

    def __init__(
        self,
        throttler: Any,  # Type as Any to avoid direct dependency
        web_assistants_factory: Any,  # Type as Any to avoid direct dependency
        logger: Optional[Logger] = None,
    ):
        """Initialize the client with Hummingbot components.

        :param throttler: Hummingbot AsyncThrottler instance
        :param web_assistants_factory: Hummingbot WebAssistantsFactory instance
        :param logger: Logger instance
        """
        if not HUMMINGBOT_AVAILABLE:
            raise ImportError("Hummingbot components are not available")

        self._throttler = throttler
        self._web_assistants_factory = web_assistants_factory
        self._throttler_adapter = HummingbotThrottlerAdapter(throttler)
        self._logger = logger or logging.getLogger(__name__)
        self._rest_assistant: Optional[RESTAssistant] = None

    async def _ensure_rest_assistant(self):
        """Ensure REST assistant is initialized."""
        if self._rest_assistant is None:
            self._rest_assistant = await self._web_assistants_factory.get_rest_assistant()

    async def get_rest_data(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        method: str = "GET",
    ) -> Any:
        """Get data from REST API using Hummingbot's REST assistant.

        :param url: REST API URL
        :param params: Query parameters
        :param data: Request body data
        :param headers: Request headers
        :param method: HTTP method
        :return: REST API response
        """
        await self._ensure_rest_assistant()

        # Clean params and data, removing None values
        cleaned_params = (
            None if params is None else {k: v for k, v in params.items() if v is not None}
        )
        cleaned_data = None if data is None else {k: v for k, v in data.items() if v is not None}

        try:
            response = await self._rest_assistant.call(
                url=url,
                params=cleaned_params,
                data=json.dumps(cleaned_data) if cleaned_data else None,
                headers=headers,
                method=method,
            )
            return await response.json()
        except Exception as e:
            self._logger.error(f"REST request to {url} failed: {e}")
            raise

    async def establish_ws_connection(self, url: str) -> WSAssistant:
        """Establish a WebSocket connection using Hummingbot's WS assistant.

        :param url: WebSocket URL
        :return: Adapted WebSocket assistant
        """
        try:
            ws_assistant = await self._web_assistants_factory.get_ws_assistant()
            await ws_assistant.connect(ws_url=url)
            return HummingbotWSAssistantAdapter(ws_assistant, self._logger)
        except Exception as e:
            self._logger.error(f"WebSocket connection to {url} failed: {e}")
            raise

    async def send_ws_message(self, ws_assistant: WSAssistant, payload: dict[str, Any]) -> None:
        """Send a message over WebSocket.

        :param ws_assistant: WebSocket assistant
        :param payload: Message payload
        """
        await ws_assistant.send(payload)

    async def close(self) -> None:
        """Close all connections and clean up resources."""
        if hasattr(self._web_assistants_factory, "close"):
            await self._web_assistants_factory.close()

    async def __aenter__(self) -> "HummingbotNetworkClient":
        """Enter async context manager."""
        await self._ensure_rest_assistant()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.close()


class NetworkClientFactory:
    """Factory for creating network clients.

    This factory creates the appropriate network client based on the
    available dependencies, preferring Hummingbot components when available.
    """

    @staticmethod
    def create_client(
        hummingbot_components: Optional[dict] = None, logger: Optional[Logger] = None
    ) -> NetworkClientProtocol:
        """Create a network client.

        :param hummingbot_components: Dictionary of Hummingbot components:
            - throttler: AsyncThrottlerBase instance
            - web_assistants_factory: WebAssistantsFactory instance
        :param logger: Logger instance
        :return: NetworkClientProtocol implementation
        """
        # Try to use Hummingbot components if available
        if hummingbot_components is not None:
            throttler = hummingbot_components.get("throttler")
            web_assistants_factory = hummingbot_components.get("web_assistants_factory")

            if throttler is not None and web_assistants_factory is not None:
                try:
                    # Only import and use if the environment has Hummingbot
                    if HUMMINGBOT_AVAILABLE:
                        return HummingbotNetworkClient(
                            throttler=throttler,
                            web_assistants_factory=web_assistants_factory,
                            logger=logger,
                        )
                except (ImportError, TypeError) as e:
                    # Log the error but continue with fallback
                    if logger:
                        logger.warning(
                            f"Could not create Hummingbot network client: {e}. Falling back to standalone implementation."
                        )

        # Fall back to standalone implementation
        from candles_feed.core.network_client import NetworkClient

        return NetworkClient(logger=logger)
