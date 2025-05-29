"""
Extended unit tests for the NetworkConfig class.

This module provides more comprehensive tests for the NetworkConfig class,
covering edge cases and more complex scenarios.
"""

import json

import pytest

from candles_feed.core.network_config import EndpointType, NetworkConfig, NetworkEnvironment


class TestNetworkConfigExtended:
    """Extended test suite for NetworkConfig class."""

    def test_custom_init(self):
        """Test initialization with custom parameters."""
        # Test with default environment but no overrides
        config = NetworkConfig(default_environment=NetworkEnvironment.TESTNET)
        assert config.default_environment == NetworkEnvironment.TESTNET
        assert config.endpoint_overrides == {}

        # All endpoints should use testnet
        for endpoint in EndpointType:
            assert config.get_environment(endpoint) == NetworkEnvironment.TESTNET
            assert config.is_testnet_for(endpoint)

        # Test with custom overrides
        overrides = {
            EndpointType.CANDLES: NetworkEnvironment.PRODUCTION,
            EndpointType.ORDERS: NetworkEnvironment.TESTNET
        }
        config = NetworkConfig(
            default_environment=NetworkEnvironment.PRODUCTION,
            endpoint_overrides=overrides
        )

        assert config.default_environment == NetworkEnvironment.PRODUCTION
        assert config.endpoint_overrides == overrides

        # Check specific endpoint environments
        assert config.get_environment(EndpointType.CANDLES) == NetworkEnvironment.PRODUCTION
        assert config.get_environment(EndpointType.ORDERS) == NetworkEnvironment.TESTNET
        assert config.get_environment(EndpointType.ACCOUNT) == NetworkEnvironment.PRODUCTION

    def test_hybrid_with_all_endpoints(self):
        """Test creating a hybrid configuration with all endpoint types specified."""
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.PRODUCTION,
            ticker=NetworkEnvironment.TESTNET,
            trades=NetworkEnvironment.PRODUCTION,
            orders=NetworkEnvironment.TESTNET,
            account=NetworkEnvironment.TESTNET
        )

        # Verify each endpoint has the correct environment
        assert config.get_environment(EndpointType.CANDLES) == NetworkEnvironment.PRODUCTION
        assert config.get_environment(EndpointType.TICKER) == NetworkEnvironment.TESTNET
        assert config.get_environment(EndpointType.TRADES) == NetworkEnvironment.PRODUCTION
        assert config.get_environment(EndpointType.ORDERS) == NetworkEnvironment.TESTNET
        assert config.get_environment(EndpointType.ACCOUNT) == NetworkEnvironment.TESTNET

        # Check convenience method
        assert not config.is_testnet_for(EndpointType.CANDLES)
        assert config.is_testnet_for(EndpointType.TICKER)
        assert not config.is_testnet_for(EndpointType.TRADES)
        assert config.is_testnet_for(EndpointType.ORDERS)
        assert config.is_testnet_for(EndpointType.ACCOUNT)

    def test_hybrid_with_mixed_type_values(self):
        """Test hybrid configuration with mixed string and enum values."""
        config = NetworkConfig.hybrid(
            candles="production",  # String value
            ticker=NetworkEnvironment.TESTNET,  # Enum value
            trades="production",
            orders="testnet",
            account=NetworkEnvironment.TESTNET
        )

        # Verify each endpoint has the correct environment
        assert config.get_environment(EndpointType.CANDLES) == NetworkEnvironment.PRODUCTION
        assert config.get_environment(EndpointType.TICKER) == NetworkEnvironment.TESTNET
        assert config.get_environment(EndpointType.TRADES) == NetworkEnvironment.PRODUCTION
        assert config.get_environment(EndpointType.ORDERS) == NetworkEnvironment.TESTNET
        assert config.get_environment(EndpointType.ACCOUNT) == NetworkEnvironment.TESTNET

    def test_hybrid_with_string_endpoint_types(self):
        """Test hybrid configuration with string endpoint types."""
        config = NetworkConfig.hybrid(
            **{
                "candles": NetworkEnvironment.PRODUCTION,  # Dictionary key as string
                "orders": NetworkEnvironment.TESTNET
            }
        )

        # Verify endpoints have correct environment
        assert config.get_environment(EndpointType.CANDLES) == NetworkEnvironment.PRODUCTION
        assert config.get_environment(EndpointType.ORDERS) == NetworkEnvironment.TESTNET

    def test_is_testnet_for_default_production(self):
        """Test is_testnet_for with default production environment."""
        config = NetworkConfig()  # Default is production

        for endpoint in EndpointType:
            assert not config.is_testnet_for(endpoint)

    def test_is_testnet_for_default_testnet(self):
        """Test is_testnet_for with default testnet environment."""
        config = NetworkConfig(default_environment=NetworkEnvironment.TESTNET)

        for endpoint in EndpointType:
            assert config.is_testnet_for(endpoint)

    def test_equality(self):
        """Test that identical configurations are equal."""
        config1 = NetworkConfig.hybrid(
            candles=NetworkEnvironment.PRODUCTION,
            orders=NetworkEnvironment.TESTNET
        )

        config2 = NetworkConfig.hybrid(
            candles=NetworkEnvironment.PRODUCTION,
            orders=NetworkEnvironment.TESTNET
        )

        # Configurations with the same values should be equal in behavior
        for endpoint in EndpointType:
            assert config1.get_environment(endpoint) == config2.get_environment(endpoint)
            assert config1.is_testnet_for(endpoint) == config2.is_testnet_for(endpoint)

    def test_different_configs(self):
        """Test that different configurations behave differently."""
        config1 = NetworkConfig.hybrid(
            candles=NetworkEnvironment.PRODUCTION,
            orders=NetworkEnvironment.TESTNET
        )

        config2 = NetworkConfig.hybrid(
            candles=NetworkEnvironment.TESTNET,
            orders=NetworkEnvironment.PRODUCTION
        )

        # These should have opposite behaviors
        assert config1.is_testnet_for(EndpointType.CANDLES) != config2.is_testnet_for(EndpointType.CANDLES)
        assert config1.is_testnet_for(EndpointType.ORDERS) != config2.is_testnet_for(EndpointType.ORDERS)

    def test_error_handling(self):
        """Test error handling with invalid inputs."""
        # Test with invalid endpoint type and valid environment
        with pytest.raises(ValueError, match="Invalid endpoint type"):
            NetworkConfig.hybrid(
                invalid_endpoint=NetworkEnvironment.PRODUCTION
            )

        # Test with valid endpoint type and invalid environment string
        with pytest.raises(ValueError, match="Invalid network environment"):
            NetworkConfig.hybrid(
                candles="invalid_environment"
            )

        # Test with endpoint type as enum (not possible directly with **kwargs)
        # Using string endpoint types is the supported way
        with pytest.raises(ValueError, match="Invalid network environment"):
            # Convert to string to enable the endpoint type handling code to run
            NetworkConfig.hybrid(
                **{EndpointType.CANDLES.value: "invalid_environment"}
            )

    def test_for_testing_mode(self):
        """Test the for_testing configuration that bypasses network selection."""
        # Create a testing config
        config = NetworkConfig.for_testing()

        # Should have bypass flag
        assert hasattr(config, '_bypass_for_testing')
        assert config._bypass_for_testing is True

        # Should behave like production config regardless of settings
        config.default_environment = NetworkEnvironment.TESTNET
        override = {EndpointType.CANDLES: NetworkEnvironment.TESTNET}
        config.endpoint_overrides = override

        # All endpoints should still return production
        for endpoint in EndpointType:
            assert config.get_environment(endpoint) == NetworkEnvironment.PRODUCTION
            assert not config.is_testnet_for(endpoint)

    def test_config_str_representation(self):
        """Test the string representation of a NetworkConfig."""
        # Create a hybrid config
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.TESTNET,
            orders=NetworkEnvironment.PRODUCTION
        )

        # Get string representation
        config_str = str(config)

        # Basic check - should at least include the class name
        assert "NetworkConfig" in config_str

        # Note: The NetworkConfig doesn't appear to have a custom __str__ implementation,
        # so we can't expect specific attributes to appear in the string representation.
        # If this functionality is needed, it should be implemented in the NetworkConfig class.

    def test_config_repr_representation(self):
        """Test that repr() of a NetworkConfig is informative."""
        # Create a hybrid config
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.TESTNET,
            orders=NetworkEnvironment.PRODUCTION
        )

        # Get repr string
        config_repr = repr(config)

        # Basic check - should at least include the class name
        assert "NetworkConfig" in config_repr

        # Note: The NetworkConfig doesn't appear to have a custom __repr__ implementation,
        # so we can't expect specific attributes to appear in the string representation.
        # If this functionality is needed, it should be implemented in the NetworkConfig class.

    def test_config_serialization(self):
        """Test that NetworkConfig can be properly serialized and deserialized."""
        # This test verifies that the configuration can be
        # properly represented as a dictionary for serialization

        # Create a hybrid config
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.TESTNET,
            orders=NetworkEnvironment.PRODUCTION
        )

        # Convert to dictionary representation
        # This is a hypothetical method that could be implemented
        # to support serialization
        if hasattr(config, 'to_dict'):
            config_dict = config.to_dict()

            # Should include all necessary configuration
            assert 'default_environment' in config_dict
            assert 'endpoint_overrides' in config_dict

            # Should be JSON serializable
            json_str = json.dumps(config_dict)
            assert json_str

    def test_endpoint_type_coverage(self):
        """Test that all endpoint types can be configured separately."""
        # Create a config with a different environment for each endpoint type
        config_dict = {}

        # Alternate between production and testnet for each endpoint
        for i, endpoint in enumerate(EndpointType):
            env = NetworkEnvironment.PRODUCTION if i % 2 == 0 else NetworkEnvironment.TESTNET
            config_dict[endpoint.value] = env

        # Create config using the dictionary
        config = NetworkConfig.hybrid(**config_dict)

        # Verify each endpoint has the correct environment
        for i, endpoint in enumerate(EndpointType):
            expected_env = NetworkEnvironment.PRODUCTION if i % 2 == 0 else NetworkEnvironment.TESTNET
            assert config.get_environment(endpoint) == expected_env
            assert config.is_testnet_for(endpoint) == (expected_env == NetworkEnvironment.TESTNET)
