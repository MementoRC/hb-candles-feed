"""
Network communication client for the Candle Feed framework.
"""

import json
import logging
import weakref
from typing import Any, cast

import aiohttp

from candles_feed.core.network_config import NetworkConfig
from candles_feed.core.protocols import Logger, WSAssistant

# Global registry to track unclosed sessions for defensive cleanup
_ACTIVE_SESSIONS: weakref.WeakSet[aiohttp.ClientSession] = weakref.WeakSet()


class NetworkClient:
    """Handles network communication with exchanges.

    This class provides methods for communicating with exchange APIs,
    handling both REST and WebSocket connections with optimized connection pooling.
    """

    def __init__(self, config: NetworkConfig | None = None, logger: Logger | None = None):
        """Initialize the NetworkClient.

        :param config: Network configuration for connection pooling and timeouts
        :param logger: Logger instance
        """
        self.logger: Logger = logger or cast("Logger", logging.getLogger(__name__))
        self.config = config or NetworkConfig()
        self._session: aiohttp.ClientSession | None = None
        self._connector: aiohttp.TCPConnector | None = None

    async def _ensure_session(self):
        """Ensure aiohttp session exists with optimized connection pooling."""
        if self._session is None or self._session.closed:
            # Create optimized TCP connector for connection pooling
            if self._connector is None or self._connector.closed:
                self._connector = aiohttp.TCPConnector(
                    limit=self.config.max_connections_per_host * 4,  # Total pool size
                    limit_per_host=self.config.max_connections_per_host,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True,
                    ttl_dns_cache=300,  # DNS cache for 5 minutes
                    use_dns_cache=True,
                )

            # Create timeout configuration
            timeout = aiohttp.ClientTimeout(
                total=self.config.rest_api_timeout,
                connect=min(10.0, self.config.rest_api_timeout / 2),
                sock_read=self.config.rest_api_timeout,
                sock_connect=min(5.0, self.config.rest_api_timeout / 4),
            )

            # Create session with optimized settings
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers={
                    "User-Agent": "Candles-Feed/1.0",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                },
            )

            # Track session for defensive cleanup
            _ACTIVE_SESSIONS.add(self._session)

    async def close(self):
        """Close the client session and connector.

        Should be called when the network client is no longer needed
        to properly clean up resources.
        """
        if self._session and not self._session.closed:
            await self._session.close()
            # Remove from tracking set if still there
            _ACTIVE_SESSIONS.discard(self._session)
            self._session = None

        if self._connector and not self._connector.closed:
            await self._connector.close()
            self._connector = None

    async def __aenter__(self):
        """Async context manager enter method."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit method."""
        await self.close()

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
        :raises Exception: If the request fails
        """
        await self._ensure_session()
        assert self._session is not None

        self.logger.debug(f"Making REST request to {url} with params {params}")

        # Clean params, removing None values to avoid serialization issues
        cleaned_params = None
        if params is not None:
            cleaned_params = {k: v for k, v in params.items() if v is not None}

        # Clean data, removing None values
        cleaned_data = None
        if data is not None:
            cleaned_data = {k: v for k, v in data.items() if v is not None}

        try:
            async with self._session.request(
                method=method, url=url, params=cleaned_params, json=cleaned_data, headers=headers
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            self.logger.error(f"REST request failed: {e}")
            raise

    def get_connection_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics for performance monitoring.

        :return: Dictionary with connection pool statistics
        """
        if not self._connector:
            return {"status": "not_initialized"}

        stats = {
            "total_connections": len(self._connector._conns),
            "available_connections": sum(len(conns) for conns in self._connector._conns.values()),
            "connector_closed": self._connector.closed,
            "keepalive_timeout": getattr(self._connector, "_keepalive_timeout", None),
            "limit": getattr(self._connector, "_limit", None),
            "limit_per_host": getattr(self._connector, "_limit_per_host", None),
        }

        return stats

    async def establish_ws_connection(self, url: str) -> WSAssistant:
        """Establish a websocket connection.

        :param url: WebSocket URL
        :return: WSAssistant instance
        :raises Exception: If the connection fails
        """
        await self._ensure_session()
        assert self._session is not None

        self.logger.debug(f"Establishing WebSocket connection to {url}")

        try:
            ws = await self._session.ws_connect(url=url)
            return SimpleWSAssistant(ws, self.logger)
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {e}")
            raise

    async def send_ws_message(self, ws_assistant: WSAssistant, payload: dict[str, Any]) -> None:
        """Send a message over WebSocket.

        :param ws_assistant: WebSocket assistant
        :param payload: Message payload
        :raises Exception: If sending fails
        """
        try:
            await ws_assistant.send(payload)
        except Exception as e:
            self.logger.error(f"Failed to send WebSocket message: {e}")
            raise


class SimpleWSAssistant(WSAssistant):
    """Simple implementation of WSAssistant using aiohttp."""

    def __init__(
        self, ws_connection: aiohttp.ClientWebSocketResponse, logger: Logger | None = None
    ):
        """Initialize the SimpleWSAssistant.

        :param ws_connection: WebSocket connection
        :param logger: Logger instance
        """
        self._ws = ws_connection
        self._logger = logger or logging.getLogger(__name__)

    async def connect(self) -> None:
        """Connect to WebSocket. No-op as already connected in establish_ws_connection."""
        pass

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        if not self._ws.closed:
            await self._ws.close()

    async def send(self, payload: dict[str, Any]) -> None:
        """Send a message over WebSocket.

        :param payload: Message payload
        :raises Exception: If sending fails
        """
        await self._ws.send_json(payload)

    async def iter_messages(self):
        """Iterate through incoming messages.

        This method implements an async iterator protocol.

        :yield: WebSocket messages
        """
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        yield json.loads(msg.data)
                    except json.JSONDecodeError:
                        self._logger.error(f"Failed to parse WebSocket message: {msg.data}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self._logger.error(f"WebSocket error: {msg}")
                    break
        except Exception as e:
            self._logger.error(f"Error iterating WebSocket messages: {e}")
            raise

    def __aiter__(self):
        """Return self as an async iterator.

        This method is required for the async iterator protocol.

        :return: Async iterator for messages
        """
        return self.iter_messages()


async def cleanup_unclosed_sessions():
    """Defensive cleanup of any unclosed sessions.

    This function can be called during shutdown or testing to ensure
    no aiohttp sessions are left unclosed.
    """
    import contextlib

    sessions_to_close = list(_ACTIVE_SESSIONS)
    for session in sessions_to_close:
        if not session.closed:
            with contextlib.suppress(Exception):
                await session.close()
    _ACTIVE_SESSIONS.clear()
