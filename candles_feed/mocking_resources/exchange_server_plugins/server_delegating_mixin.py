"""
Route handlers that delegate to the generic MockedExchangeServer logic.

A plugin using this mixin only translates formats (REST params and payloads, WebSocket
subscribe messages and candle messages). Candle lookup, time filtering, subscription
bookkeeping and live pushes are done by the server.
"""

import json
from typing import Any

from aiohttp import web

_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


class ServerDelegatingMixin:
    """REST klines and WebSocket handlers backed by the server's generic implementation."""

    @staticmethod
    def _interval_to_seconds(interval: str) -> int:
        """
        Convert a standard interval string (e.g. "5m") to seconds.

        The server uses this when generating candles for a trading pair.

        :param interval: The interval string.
        :returns: The interval in seconds.
        :raises ValueError: If the interval unit is unknown.
        """
        unit = _UNIT_SECONDS.get(interval[-1])
        if unit is None:
            raise ValueError(f"Unknown interval unit: {interval[-1]}")
        return int(interval[:-1]) * unit

    @staticmethod
    def is_ws_unsubscribe(message: dict[str, Any]) -> bool:
        """
        Tell whether a client message asks to unsubscribe.

        :param message: The decoded client message.
        :returns: True if any of the common verb fields mentions an unsubscribe.
        """
        return any(
            "unsub" in str(message.get(key, "")).lower()
            for key in ("op", "action", "method", "type")
        )

    async def handle_klines(self, server, request: web.Request) -> web.Response:
        """
        Serve a candle request using the server's generic klines handler.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: JSON response with candle data in the plugin's format.
        """
        return await server.handle_klines(request)

    async def handle_websocket(self, server, request: web.Request) -> web.WebSocketResponse:
        """
        Serve a WebSocket connection by routing messages to the server's subscription logic.

        :param server: The mock server instance.
        :param request: The web request.
        :returns: The WebSocket response.
        """
        client_ip = request.remote
        if not server._check_rate_limit(client_ip, "ws"):
            return web.Response(status=429, text="Too many requests")  # type: ignore[return-value]

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        server.ws_connections.add(ws)

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.ERROR:
                    break
                if msg.type != web.WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(msg.data)
                    if self.is_ws_unsubscribe(data):
                        await server._handle_unsubscription(ws, data)
                    else:
                        await server._handle_subscription(ws, data, client_ip)
                except json.JSONDecodeError:
                    await ws.send_json({"error": "Invalid JSON"})
                except Exception as e:
                    server.logger.error(f"Error handling WebSocket message: {e}")
                    await ws.send_json({"error": f"Error: {e}"})
        finally:
            server._cleanup_websocket(ws)

        return ws
