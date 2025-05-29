"""
Unit tests for the NetworkConfig class and related functionality.

This module tests the various configuration options, environment selection,
and helper methods available in the NetworkConfig class.
"""

import pytest

from candles_feed.core.network_config import EndpointType, NetworkConfig, NetworkEnvironment


class TestNetworkConfig:
    """Test suite for NetworkConfig class."""

    def test_default_environment(self):
        """Test the default environment when creating a NetworkConfig."""
        config = NetworkConfig()
        assert config.default_environment == NetworkEnvironment.PRODUCTION

        # All endpoints should use production by default
        for endpoint in EndpointType:
            assert config.get_environment(endpoint) == NetworkEnvironment.PRODUCTION
            assert not config.is_testnet_for(endpoint)

    def test_testnet_configuration(self):
        """Test creating a testnet-only configuration."""
        config = NetworkConfig.testnet()
        assert config.default_environment == NetworkEnvironment.TESTNET

        # All endpoints should use testnet
        for endpoint in EndpointType:
            assert config.get_environment(endpoint) == NetworkEnvironment.TESTNET
            assert config.is_testnet_for(endpoint)

    def test_production_configuration(self):
        """Test creating a production-only configuration."""
        config = NetworkConfig.production()
        assert config.default_environment == NetworkEnvironment.PRODUCTION

        # All endpoints should use production
        for endpoint in EndpointType:
            assert config.get_environment(endpoint) == NetworkEnvironment.PRODUCTION
            assert not config.is_testnet_for(endpoint)

    def test_hybrid_configuration(self):
        """Test creating a hybrid configuration with specific overrides."""
        # Create a hybrid config with candles in production but orders in testnet
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.PRODUCTION,
            orders=NetworkEnvironment.TESTNET
        )

        # Check default environment
        assert config.default_environment == NetworkEnvironment.PRODUCTION

        # Check specific endpoint environments
        assert config.get_environment(EndpointType.CANDLES) == NetworkEnvironment.PRODUCTION
        assert config.get_environment(EndpointType.ORDERS) == NetworkEnvironment.TESTNET
        assert config.get_environment(EndpointType.ACCOUNT) == NetworkEnvironment.PRODUCTION

        # Check convenience methods
        assert not config.is_testnet_for(EndpointType.CANDLES)
        assert config.is_testnet_for(EndpointType.ORDERS)
        assert not config.is_testnet_for(EndpointType.ACCOUNT)

    def test_hybrid_configuration_with_string_values(self):
        """Test hybrid configuration with string values instead of enums."""
        config = NetworkConfig.hybrid(
            candles="production",
            orders="testnet"
        )

        # Check endpoints have correct environment
        assert config.get_environment(EndpointType.CANDLES) == NetworkEnvironment.PRODUCTION
        assert config.get_environment(EndpointType.ORDERS) == NetworkEnvironment.TESTNET

    def test_hybrid_configuration_with_invalid_values(self):
        """Test that invalid values raise appropriate errors."""
        # Test invalid endpoint type
        with pytest.raises(ValueError, match="Invalid endpoint type"):
            NetworkConfig.hybrid(invalid_endpoint="production")

        # Test invalid environment
        with pytest.raises(ValueError, match="Invalid network environment"):
            NetworkConfig.hybrid(candles="invalid_environment")

    def test_testing_configuration(self):
        """Test the for_testing configuration that bypasses network selection."""
        config = NetworkConfig.for_testing()

        # Verify the bypass flag is set
        assert getattr(config, '_bypass_for_testing', False) is True

        # Even if we set it as a testnet config, it should return production values
        config.default_environment = NetworkEnvironment.TESTNET

        # All endpoints should return production despite the testnet setting
        for endpoint in EndpointType:
            assert config.get_environment(endpoint) == NetworkEnvironment.PRODUCTION
            assert not config.is_testnet_for(endpoint)
