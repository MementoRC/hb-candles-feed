"""
Network configuration classes for supporting testnet and production environments.

This module provides classes for configuring network environments (production or testnet)
for different types of API endpoints.
"""

from enum import Enum
from typing import Dict, Optional


class EndpointType(Enum):
    """Types of endpoints that can be configured with different network environments."""
    CANDLES = "candles"      # Candle data endpoints
    TICKER = "ticker"        # Ticker data endpoints
    TRADES = "trades"        # Trade data endpoints
    ORDERS = "orders"        # Order management endpoints
    ACCOUNT = "account"      # Account information endpoints


class NetworkEnvironment(Enum):
    """Available network environments."""
    PRODUCTION = "production"
    TESTNET = "testnet"


class NetworkConfig:
    """Configuration for network endpoints.

    This class allows configuring which network environment (production or testnet)
    to use for each type of endpoint.
    """

    def __init__(
        self,
        default_environment: NetworkEnvironment = NetworkEnvironment.PRODUCTION,
        endpoint_overrides: Optional[Dict[EndpointType, NetworkEnvironment]] = None
    ):
        """Initialize network configuration.

        :param default_environment: Default environment for all endpoints
        :param endpoint_overrides: Specific overrides for individual endpoint types
        """
        self.default_environment = default_environment
        self.endpoint_overrides = endpoint_overrides or {}

        # For testing only - when True, will always return production regardless of settings
        self._bypass_for_testing = False

    def get_environment(self, endpoint_type: EndpointType) -> NetworkEnvironment:
        """Get the environment to use for a specific endpoint type.

        :param endpoint_type: The type of endpoint
        :return: The environment to use for this endpoint type
        """
        if getattr(self, '_bypass_for_testing', False):
            return NetworkEnvironment.PRODUCTION
        return self.endpoint_overrides.get(endpoint_type, self.default_environment)

    def is_testnet_for(self, endpoint_type: EndpointType) -> bool:
        """Check if testnet should be used for a specific endpoint type.

        :param endpoint_type: The type of endpoint
        :return: True if testnet should be used, False for production
        """
        if getattr(self, '_bypass_for_testing', False):
            return False
        return self.get_environment(endpoint_type) == NetworkEnvironment.TESTNET

    @classmethod
    def production(cls) -> 'NetworkConfig':
        """Create a production-only configuration.

        :return: NetworkConfig configured to use production for all endpoints
        """
        return cls(default_environment=NetworkEnvironment.PRODUCTION)

    @classmethod
    def testnet(cls) -> 'NetworkConfig':
        """Create a testnet-only configuration.

        :return: NetworkConfig configured to use testnet for all endpoints
        """
        return cls(default_environment=NetworkEnvironment.TESTNET)

    @classmethod
    def hybrid(cls, **endpoint_overrides) -> 'NetworkConfig':
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
        processed_overrides = {}
        for key, value in endpoint_overrides.items():
            if isinstance(key, str):
                try:
                    key = EndpointType(key)
                except ValueError:
                    raise ValueError(f"Invalid endpoint type: {key}") from None
            if isinstance(value, str):
                try:
                    value = NetworkEnvironment(value)
                except ValueError:
                    raise ValueError(f"Invalid network environment: {value}") from None
            processed_overrides[key] = value

        return cls(
            default_environment=NetworkEnvironment.PRODUCTION,
            endpoint_overrides=processed_overrides
        )

    @classmethod
    def for_testing(cls) -> 'NetworkConfig':
        """Create a configuration suitable for testing with mock servers.

        This configuration will always return production URLs regardless of settings,
        allowing for easier patching in tests.

        :return: NetworkConfig configured with testing bypass
        """
        config = cls.production()
        config._bypass_for_testing = True
        return config
