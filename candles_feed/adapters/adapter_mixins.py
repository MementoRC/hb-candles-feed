"""
Adapter mixins for the Candle Feed framework.

This module provides mixins that implement common adapter patterns
to reduce code duplication.
"""

import asyncio
import logging
from abc import abstractmethod
from typing import Any, Protocol

from candles_feed.core.candle_data import CandleData
from candles_feed.core.network_config import EndpointType, NetworkConfig
from candles_feed.core.protocols import NetworkClientProtocol


class SyncOnlyAdapter:
    """Mixin for adapters that only implement synchronous operations.

    This mixin implements the async interface by wrapping the synchronous method.
    """

    @abstractmethod
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
            None, self.fetch_rest_candles_synchronous, trading_pair, interval, start_time, limit
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
        def _get_rest_params(
            self, trading_pair: str, interval: str, start_time: int | None = None, limit: int = 500
        ) -> dict: ...

        def _get_rest_url(self) -> str: ...

        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]: ...

    @staticmethod
    async def _fetch_rest_candles(
        adapter_implementation: AdapterImplementationProtocol,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,  # Default matches AdapterProtocol.fetch_rest_candles
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
            trading_pair=trading_pair, interval=interval, start_time=start_time, limit=limit
        )

        url = adapter_implementation._get_rest_url()
        response = await network_client.get_rest_data(url=url, params=params)

        return adapter_implementation._parse_rest_response(response)


class TestnetSupportMixin:
    """Mixin for adapters that support testnet environments.

    This mixin enables adapters to use different URLs for testnet and
    production environments based on endpoint type.
    """

    def __init__(self, *args, network_config: NetworkConfig | None = None, **kwargs):
        """Initialize with network configuration.

        :param network_config: Network environment configuration
        :param args: Positional arguments to pass to parent class
        :param kwargs: Keyword arguments to pass to parent class
        """
        # Default to production if not specified
        self.network_config = network_config or NetworkConfig.production()

        # Used for testing to bypass network environment selection
        self._bypass_network_selection = False

        # Log current configuration
        self._log_testnet_status()

        # Call parent __init__ to ensure proper initialization chain
        super().__init__(*args, **kwargs)

    def _get_rest_url(self) -> str:
        """Get REST URL based on configuration for candles endpoint.

        This method overrides the base adapter's _get_rest_url method to
        use either production or testnet URL based on the network configuration.

        :return: REST API URL for configured environment
        """
        # Allow tests to bypass network selection
        # Allow tests to bypass network selection
        if getattr(self, "_bypass_network_selection", False):
            return self._get_production_rest_url()  # type: ignore[attr-defined]

        if self.network_config.is_testnet_for(EndpointType.CANDLES):
            return self._get_testnet_rest_url()
        return self._get_production_rest_url()

    def _get_ws_url(self) -> str:
        """Get WebSocket URL based on configuration for candles endpoint.

        This method overrides the base adapter's _get_ws_url method to
        use either production or testnet URL based on the network configuration.

        :return: WebSocket URL for configured environment
        """
        # Allow tests to bypass network selection
        # Allow tests to bypass network selection
        if getattr(self, "_bypass_network_selection", False):
            return self._get_production_ws_url()  # type: ignore[attr-defined]

        if self.network_config.is_testnet_for(EndpointType.CANDLES):
            return self._get_testnet_ws_url()
        return self._get_production_ws_url()

    @abstractmethod
    def _get_production_rest_url(self) -> str:
        """Get production REST URL for candles.

        This method must be implemented by subclasses that support testnet.

        :return: Production REST API URL
        :raises NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError(
            f"Production REST URL not implemented for {self.__class__.__name__}"
        )

    @abstractmethod
    def _get_production_ws_url(self) -> str:
        """Get production WebSocket URL.

        This method must be implemented by subclasses that support testnet.

        :return: Production WebSocket URL
        :raises NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError(
            f"Production WebSocket URL not implemented for {self.__class__.__name__}"
        )

    @abstractmethod
    def _get_testnet_rest_url(self) -> str:
        """Get testnet REST URL for candles.

        This method must be implemented by subclasses that support testnet.

        :return: Testnet REST API URL
        :raises NotImplementedError: If testnet is not supported by this adapter
        """
        raise NotImplementedError(f"Testnet REST URL not implemented for {self.__class__.__name__}")

    def _get_testnet_ws_url(self) -> str:
        """Get testnet WebSocket URL.

        This method must be implemented by subclasses that support testnet.

        :return: Testnet WebSocket URL
        :raises NotImplementedError: If testnet is not supported by this adapter
        """
        raise NotImplementedError(
            f"Testnet WebSocket URL not implemented for {self.__class__.__name__}"
        )

    def supports_testnet(self) -> bool:
        """Check if testnet is supported by this adapter.

        :return: True if testnet is supported, False otherwise
        """
        try:
            # Try to get testnet URLs without using them
            self._get_testnet_rest_url()  # type: ignore[attr-defined]
            self._get_testnet_ws_url()  # type: ignore[attr-defined]
            return True
        except NotImplementedError:
            return False

    def _log_testnet_status(self) -> None:
        """Log the testnet status for this adapter.

        This is useful for debugging and informational purposes.
        """
        logger = logging.getLogger(self.__class__.__module__)

        testnet_endpoints = []
        production_endpoints = []

        # Categorize endpoints by environment
        for endpoint_type in EndpointType:
            if self.network_config.is_testnet_for(endpoint_type):
                testnet_endpoints.append(endpoint_type.value)
            else:
                production_endpoints.append(endpoint_type.value)

        # Log the configuration
        if testnet_endpoints:
            logger.info(
                f"{self.__class__.__name__} using TESTNET for: {', '.join(testnet_endpoints)}"
            )

        if production_endpoints:
            logger.info(
                f"{self.__class__.__name__} using PRODUCTION for: {', '.join(production_endpoints)}"
            )


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
