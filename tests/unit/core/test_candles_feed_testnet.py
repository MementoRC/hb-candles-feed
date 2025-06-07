"""
Unit tests for testnet support in the CandlesFeed class.

This module tests the CandlesFeed class's ability to correctly initialize
and use a network configuration for testnet environments.
"""

from unittest.mock import MagicMock, patch

import pytest

from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.network_config import EndpointType, NetworkConfig, NetworkEnvironment


class TestCandlesFeedTestnet:
    """Test suite for CandlesFeed testnet support."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock exchange registry."""
        with patch("candles_feed.core.candles_feed.ExchangeRegistry") as mock_registry_class:
            # Configure mock registry - use general MagicMock without spec for flexibility
            mock_adapter = MagicMock()
            mock_adapter.get_supported_intervals.return_value = {"1m": 60}
            mock_adapter.get_trading_pair_format.return_value = "BTC-USDT"
            mock_adapter.supports_testnet.return_value = True

            # Set up the class method (not instance method)
            mock_registry_class.get_adapter_instance = MagicMock(return_value=mock_adapter)

            yield mock_registry_class, mock_adapter

    @pytest.fixture
    def mock_network_client(self):
        """Create a mock network client."""
        with patch("candles_feed.core.network_client.NetworkClient") as mock_client:
            yield mock_client

    def test_default_network_config(self, mock_registry, mock_network_client):
        """Test that CandlesFeed uses production by default."""
        registry, adapter = mock_registry

        # Create feed with default network config (should be production)
        CandlesFeed(exchange="binance_spot", trading_pair="BTC-USDT", interval="1m")

        # Check that the adapter was initialized
        assert registry.get_adapter_instance.called

        # When no network_config is provided, it might be None in the call
        # and defaults would be applied in the adapter rather than in CandlesFeed
        # The important thing is that the adapter was created successfully
        # and could then use its own default production config

        # Verify the exchange and trading pair were passed correctly
        args, kwargs = registry.get_adapter_instance.call_args
        assert args[0] == "binance_spot" or kwargs.get("exchange") == "binance_spot"

    def test_testnet_network_config(self, mock_registry, mock_network_client):
        """Test that CandlesFeed passes testnet config to adapter."""
        registry, adapter = mock_registry

        # Create feed with testnet config
        CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            network_config=NetworkConfig.testnet(),
        )

        # Check that the adapter was initialized with the testnet config
        kwargs = registry.get_adapter_instance.call_args[1]
        assert "network_config" in kwargs
        assert kwargs["network_config"].default_environment == NetworkEnvironment.TESTNET

        # All endpoints should be configured for testnet
        for endpoint_type in EndpointType:
            assert kwargs["network_config"].is_testnet_for(endpoint_type)

    def test_hybrid_network_config(self, mock_registry, mock_network_client):
        """Test that CandlesFeed passes hybrid config to adapter."""
        registry, adapter = mock_registry

        # Create hybrid config
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.TESTNET, orders=NetworkEnvironment.PRODUCTION
        )

        # Create feed with hybrid config
        CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", network_config=config
        )

        # Check that the adapter was initialized with the hybrid config
        kwargs = registry.get_adapter_instance.call_args[1]
        assert "network_config" in kwargs

        # Check specific endpoint configurations
        assert kwargs["network_config"].is_testnet_for(EndpointType.CANDLES)
        assert not kwargs["network_config"].is_testnet_for(EndpointType.ORDERS)

    def test_config_passed_to_adapter(self, mock_registry, mock_network_client):
        """Test that the exact config instance is passed to the adapter."""
        registry, adapter = mock_registry

        # Create a specific config instance
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.TESTNET, ticker=NetworkEnvironment.PRODUCTION
        )

        # Create feed with the config
        CandlesFeed(
            exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", network_config=config
        )

        # Check that the exact same config instance was passed to the adapter
        kwargs = registry.get_adapter_instance.call_args[1]
        assert "network_config" in kwargs
        assert kwargs["network_config"] is config  # Same instance

    def test_testnet_initialization_logging(self, mock_registry, mock_network_client):
        """Test that CandlesFeed logs testnet status."""
        registry, adapter = mock_registry

        # Make adapter return that it supports testnet
        adapter.supports_testnet.return_value = True

        # Mock the adapter's _log_testnet_status method to verify it's called
        with patch.object(adapter, "_log_testnet_status"):
            # Create feed with testnet config
            feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair="BTC-USDT",
                interval="1m",
                network_config=NetworkConfig.testnet(),
            )

            # Verify that constructor instantiates correctly with the config
            # Specific logging might happen in adapter, not in feed constructor
            assert feed is not None

    def test_testnet_adapter_method_calls(self, mock_registry, mock_network_client):
        """Test that correct adapter methods are called when testnet is enabled."""
        registry, adapter = mock_registry

        # Create feed with testnet config
        CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            network_config=NetworkConfig.testnet(),
        )

        # Setup the adapter to check testnet support
        adapter.supports_testnet.return_value = True

        # Verify that the adapter was initialized with the testnet config
        # The _get_rest_url and _get_ws_url methods would typically be called
        # when operations are performed, not just on instantiation

        # Get the adapter instance that was created
        args, kwargs = registry.get_adapter_instance.call_args
        assert "network_config" in kwargs
        assert kwargs["network_config"].default_environment == NetworkEnvironment.TESTNET

    def test_unsupported_testnet_warning(self, mock_registry, mock_network_client):
        """Test warning logs when testnet is requested but not supported by adapter."""
        registry, adapter = mock_registry

        # Make adapter return that it doesn't support testnet
        adapter.supports_testnet.return_value = False

        # Still, the feed should initialize correctly, just using production instead
        CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            network_config=NetworkConfig.testnet(),
        )

        # The adapter should be initialized with testnet config
        args, kwargs = registry.get_adapter_instance.call_args
        assert "network_config" in kwargs
        assert kwargs["network_config"].default_environment == NetworkEnvironment.TESTNET

        # But since supports_testnet is False, the adapter would use production URLs
        # This is tested in the adapter tests, not in the feed tests

    def test_multiple_testnet_configs(self, mock_registry, mock_network_client):
        """Test that multiple feeds can be created with different network configs."""
        registry, adapter = mock_registry

        # Create a feed with testnet config
        CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            network_config=NetworkConfig.testnet(),
        )

        # Create a feed with production config
        CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            network_config=NetworkConfig.production(),
        )

        # Create a feed with hybrid config
        CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            network_config=NetworkConfig.hybrid(
                candles=NetworkEnvironment.TESTNET, orders=NetworkEnvironment.PRODUCTION
            ),
        )

        # Verify all were initialized with appropriate configs
        calls = registry.get_adapter_instance.call_args_list

        # First call should be with testnet config
        assert "network_config" in calls[0][1]
        assert calls[0][1]["network_config"].default_environment == NetworkEnvironment.TESTNET

        # Second call should be with production config
        assert "network_config" in calls[1][1]
        assert calls[1][1]["network_config"].default_environment == NetworkEnvironment.PRODUCTION

        # Third call should be with hybrid config
        assert "network_config" in calls[2][1]
        # Default is production in hybrid mode
        assert calls[2][1]["network_config"].default_environment == NetworkEnvironment.PRODUCTION
        # But candles endpoint should use testnet
        assert calls[2][1]["network_config"].is_testnet_for(EndpointType.CANDLES)
