"""
Adapter mixins for the Candle Feed framework.

This module provides mixins that implement common adapter patterns
to reduce code duplication.
"""

import asyncio
from abc import abstractmethod
from typing import Any, Protocol

from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol


class SyncOnlyAdapter:
    """Mixin for adapters that only implement synchronous operations.
    
    This mixin implements the async interface by wrapping the synchronous method.
    """
    
    @abstractmethod
    def fetch_rest_candles_synchronous(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
    ) -> list[CandleData]:
        """Required implementation for synchronous REST candle fetching.
        
        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: List of CandleData objects
        """
        pass
    
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Convert synchronous call to async using executor.
        
        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :param network_client: Ignored for sync adapters
        :returns: List of CandleData objects
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
             self.fetch_rest_candles_synchronous,
            trading_pair, interval, start_time, limit
        )


class AsyncOnlyAdapter:
    """Mixin for adapters that only implement asynchronous operations.
    
    This mixin provides a default implementation that raises NotImplementedError
    for the synchronous method.
    """
    
    def fetch_rest_candles_synchronous(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
    ) -> list[CandleData]:
        """Not supported in async-only adapters.
        
        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :raises NotImplementedError: Always raised as this method is not supported
        """
        raise NotImplementedError("This adapter only supports async operations")
    
    @abstractmethod
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Required implementation for async REST candle fetching.
        
        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :param network_client: Network client to use for API requests
        :returns: List of CandleData objects
        """
        pass

    class AdapterImplementationProtocol(Protocol):
        def _get_rest_params(self, trading_pair: str, interval: str, start_time: int | None = None, limit: int = 500) -> dict:
            ...

        def _get_rest_url(self) -> str:
            ...

        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
            ...

    @staticmethod
    async def _fetch_rest_candles(
        adapter_implementation: AdapterImplementationProtocol,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles from REST API asynchronously.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :param network_client: Network client to use for API requests
        :return: List of CandleData objects
        """
        if network_client is None:
            raise ValueError("network_client is required for async operations")

        params = adapter_implementation._get_rest_params(
            trading_pair=trading_pair,
            interval=interval,
            start_time=start_time,
            limit=limit
        )

        url = adapter_implementation._get_rest_url()
        response = await network_client.get_rest_data(url=url, params=params)

        return adapter_implementation._parse_rest_response(response)


class NoWebSocketSupportMixin:
    """Mixin for adapters that don't support WebSocket connections.
    
    This mixin implements the required WebSocket methods to raise NotImplementedError.
    """
    
    def get_ws_url(self) -> str:
        """Get WebSocket URL.
        
        :raises NotImplementedError: Always raised as WebSocket is not supported
        """
        raise NotImplementedError("This adapter does not support WebSocket")
    
    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.
        
        :raises NotImplementedError: Always raised as WebSocket is not supported
        """
        raise NotImplementedError("This adapter does not support WebSocket")
    
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.
        
        :param trading_pair: Trading pair 
        :param interval: Candle interval
        :raises NotImplementedError: Always raised as WebSocket is not supported
        """
        raise NotImplementedError("This adapter does not support WebSocket")
    
    def parse_ws_message(self, data: Any) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.
        
        :param data: WebSocket message
        :raises NotImplementedError: Always raised as WebSocket is not supported
        """
        raise NotImplementedError("This adapter does not support WebSocket")