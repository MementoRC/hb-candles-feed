"""
Network configuration classes for supporting testnet and production environments.

This module provides classes for configuring network environments (production or testnet)
for different types of API endpoints.
"""

from enum import Enum
from typing import Any, Dict, Optional


class EndpointType(Enum):
    """Types of endpoints that can be configured with different network environments."""

    CANDLES = "candles"  # Candle data endpoints
    TICKER = "ticker"  # Ticker data endpoints
    TRADES = "trades"  # Trade data endpoints
    ORDERS = "orders"  # Order management endpoints
    ACCOUNT = "account"  # Account information endpoints


class NetworkEnvironment(Enum):
    """Available network environments."""

    PRODUCTION = "production"
    TESTNET = "testnet"


class NetworkConfig:
    """Configuration for network endpoints and performance settings.

    This class allows configuring which network environment (production or testnet)
    to use for each type of endpoint, as well as performance-related settings.
    """

    def __init__(
        self,
        default_environment: NetworkEnvironment = NetworkEnvironment.PRODUCTION,
        endpoint_overrides: dict[EndpointType, NetworkEnvironment] | None = None,
        # Performance settings
        rest_api_timeout: float = 30.0,
        websocket_ping_interval: float = 20.0,
        max_connections_per_host: int = 30,
        connection_pool_size: int = 100,
        enable_connection_pooling: bool = True,
        request_retry_attempts: int = 3,
        websocket_reconnect_attempts: int = 5,
    ):
        """Initialize network configuration.

        :param default_environment: Default environment for all endpoints
        :param endpoint_overrides: Specific overrides for individual endpoint types
        :param rest_api_timeout: Timeout for REST API requests in seconds
        :param websocket_ping_interval: WebSocket ping interval in seconds
        :param max_connections_per_host: Maximum connections per host
        :param connection_pool_size: Total connection pool size
        :param enable_connection_pooling: Whether to enable connection pooling
        :param request_retry_attempts: Number of retry attempts for failed requests
        :param websocket_reconnect_attempts: Number of WebSocket reconnection attempts
        """
        self.default_environment = default_environment
        self.endpoint_overrides = endpoint_overrides or {}

        # Performance settings
        self.rest_api_timeout = rest_api_timeout
        self.websocket_ping_interval = websocket_ping_interval
        self.max_connections_per_host = max_connections_per_host
        self.connection_pool_size = connection_pool_size
        self.enable_connection_pooling = enable_connection_pooling
        self.request_retry_attempts = request_retry_attempts
        self.websocket_reconnect_attempts = websocket_reconnect_attempts

        # For testing only - when True, will always return production regardless of settings
        self._bypass_for_testing = False

    def get_environment(self, endpoint_type: EndpointType) -> NetworkEnvironment:
        """Get the environment to use for a specific endpoint type.

        :param endpoint_type: The type of endpoint
        :return: The environment to use for this endpoint type
        """
        if getattr(self, "_bypass_for_testing", False):
            return NetworkEnvironment.PRODUCTION
        return self.endpoint_overrides.get(endpoint_type, self.default_environment)

    def is_testnet_for(self, endpoint_type: EndpointType) -> bool:
        """Check if testnet should be used for a specific endpoint type.

        :param endpoint_type: The type of endpoint
        :return: True if testnet should be used, False for production
        """
        if getattr(self, "_bypass_for_testing", False):
            return False
        return self.get_environment(endpoint_type) == NetworkEnvironment.TESTNET

    @classmethod
    def production(cls) -> "NetworkConfig":
        """Create a production-only configuration.

        :return: NetworkConfig configured to use production for all endpoints
        """
        return cls(default_environment=NetworkEnvironment.PRODUCTION)

    @classmethod
    def testnet(cls) -> "NetworkConfig":
        """Create a testnet-only configuration.

        :return: NetworkConfig configured to use testnet for all endpoints
        """
        return cls(default_environment=NetworkEnvironment.TESTNET)

    @classmethod
    def hybrid(
        cls, **endpoint_overrides: Any
    ) -> "NetworkConfig":  # Add : Any for **endpoint_overrides values
        """Create a hybrid configuration with specific overrides.

        Example:
            NetworkConfig.hybrid(
                candles=NetworkEnvironment.PRODUCTION,
                orders=NetworkEnvironment.TESTNET
            )

        :param endpoint_overrides: Keyword arguments mapping endpoint types to environments
        :return: NetworkConfig with specified overrides
        :raises ValueError: If an invalid endpoint type or environment is provided
        """
        # Convert string keys to EndpointType enum
        processed_overrides: dict[
            EndpointType, NetworkEnvironment
        ] = {}  # Explicitly type processed_overrides
        for key_str, value_orig in endpoint_overrides.items():  # Use key_str and value_orig
            typed_key: EndpointType
            try:
                typed_key = EndpointType(key_str)  # Assign to new variable typed_key
            except ValueError:
                raise ValueError(
                    f"Invalid endpoint type: {key_str}"
                ) from None  # Use key_str in error

            typed_value: NetworkEnvironment  # Declare typed_value
            if isinstance(value_orig, str):  # Check value_orig type
                try:
                    typed_value = NetworkEnvironment(value_orig)  # Assign to typed_value
                except ValueError:
                    raise ValueError(f"Invalid network environment: {value_orig}") from None
            elif isinstance(value_orig, NetworkEnvironment):  # Check if already NetworkEnvironment
                typed_value = value_orig  # Assign to typed_value
            else:
                # Handle unexpected type for value_orig
                raise TypeError(
                    f"Invalid value type for endpoint override: {key_str}={value_orig!r} "
                    f"(expected str or NetworkEnvironment)"
                )
            processed_overrides[typed_key] = typed_value  # Use typed_key and typed_value

        return cls(
            default_environment=NetworkEnvironment.PRODUCTION,
            endpoint_overrides=processed_overrides,
        )

    @classmethod
    def for_testing(cls) -> "NetworkConfig":
        """Create a configuration suitable for testing with mock servers.

        This configuration will always return production URLs regardless of settings,
        allowing for easier patching in tests.

        :return: NetworkConfig configured with testing bypass
        """
        config = cls.production()
        config._bypass_for_testing = True
        return config
