"""
Unit tests for Binance adapter with testnet support.

This module tests the Binance adapter's testnet URL handling
and integration with the TestnetSupportMixin.
"""

from unittest.mock import patch

from candles_feed.adapters.binance.constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_TESTNET_REST_URL,
    SPOT_TESTNET_WSS_URL,
    SPOT_WSS_URL,
)
from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.core.network_config import EndpointType, NetworkConfig, NetworkEnvironment


class TestBinanceSpotAdapterTestnet:
    """Test suite for Binance spot adapter with testnet support."""

    def test_constants_exist(self):
        """Test that the required constants for testnet exist."""
        assert SPOT_REST_URL is not None
        assert SPOT_WSS_URL is not None
        assert SPOT_TESTNET_REST_URL is not None
        assert SPOT_TESTNET_WSS_URL is not None
        assert SPOT_CANDLES_ENDPOINT is not None

        # Testnet and production should have different URLs
        assert SPOT_REST_URL != SPOT_TESTNET_REST_URL
        assert SPOT_WSS_URL != SPOT_TESTNET_WSS_URL

    def test_production_urls(self):
        """Test that the adapter returns correct production URLs."""
        adapter = BinanceSpotAdapter()

        # Check the abstract static methods implementation
        assert adapter._get_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_ws_url() == SPOT_WSS_URL

        # Check production URLs via TestnetSupportMixin interface
        assert adapter._get_production_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_production_ws_url() == SPOT_WSS_URL

        # With production config, the URLs should be production
        assert adapter._get_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_ws_url() == SPOT_WSS_URL

    def test_testnet_urls(self):
        """Test that the adapter returns correct testnet URLs when configured for testnet."""
        adapter = BinanceSpotAdapter(network_config=NetworkConfig.testnet())

        # Print debug info
        print(f"TestnetSupportMixin implementation: {hasattr(adapter, '_get_testnet_rest_url')}")
        print(
            f"Is testnet for candles: {adapter.network_config.is_testnet_for(EndpointType.CANDLES)}"
        )
        print(f"SPOT_REST_URL: {SPOT_REST_URL}")
        print(f"SPOT_TESTNET_REST_URL: {SPOT_TESTNET_REST_URL}")
        print(f"_get_rest_url: {adapter._get_rest_url()}")
        print(f"_get_testnet_rest_url: {adapter._get_testnet_rest_url()}")

        # Check testnet URLs via TestnetSupportMixin interface
        assert adapter._get_testnet_rest_url() == f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_testnet_ws_url() == SPOT_TESTNET_WSS_URL

        # With testnet config, the URLs should be testnet
        assert adapter._get_rest_url() == f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_ws_url() == SPOT_TESTNET_WSS_URL

    def test_hybrid_mode(self):
        """Test that the adapter handles hybrid mode correctly."""
        # Create a hybrid config where candles use testnet but others use production
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.TESTNET,
            orders=NetworkEnvironment.PRODUCTION,
            account=NetworkEnvironment.PRODUCTION,
        )

        adapter = BinanceSpotAdapter(network_config=config)

        # Should return testnet URLs for candles
        assert adapter._get_rest_url() == f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_ws_url() == SPOT_TESTNET_WSS_URL

        # Create a hybrid config where orders use testnet but candles use production
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.PRODUCTION,
            orders=NetworkEnvironment.TESTNET,
            account=NetworkEnvironment.TESTNET,
        )

        adapter = BinanceSpotAdapter(network_config=config)

        # Should return production URLs for candles
        assert adapter._get_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_ws_url() == SPOT_WSS_URL

    def test_supports_testnet(self):
        """Test that the adapter reports testnet support correctly."""
        adapter = BinanceSpotAdapter()
        assert adapter.supports_testnet() is True

    def test_bypass_network_selection(self):
        """Test that bypass_network_selection forces production URLs."""
        adapter = BinanceSpotAdapter(network_config=NetworkConfig.testnet())

        # Normally should return testnet URLs
        assert adapter._get_rest_url() == f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"

        # Enable bypass
        adapter._bypass_network_selection = True

        # Should now return production URLs
        assert adapter._get_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_ws_url() == SPOT_WSS_URL

    def test_endpoint_specific_urls(self):
        """Test URL selection based on specific endpoint types."""
        # Create a hybrid config with different settings for different endpoints
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.TESTNET,
            ticker=NetworkEnvironment.PRODUCTION,
            trades=NetworkEnvironment.TESTNET,
        )

        adapter = BinanceSpotAdapter(network_config=config)

        # Test with endpoint_type parameter if supported
        if hasattr(adapter, "_get_rest_url") and callable(adapter._get_rest_url):
            # Check if the method accepts endpoint_type parameter
            import inspect

            sig = inspect.signature(adapter._get_rest_url)
            if "endpoint_type" in sig.parameters:
                # Test URL selection based on endpoint type
                assert (
                    adapter._get_rest_url(endpoint_type=EndpointType.CANDLES)
                    == f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"
                )
                assert (
                    adapter._get_rest_url(endpoint_type=EndpointType.TICKER)
                    == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
                )
                assert (
                    adapter._get_rest_url(endpoint_type=EndpointType.TRADES)
                    == f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"
                )

    @patch("logging.Logger.info")
    def test_testnet_logging(self, mock_log_info):
        """Test that the adapter logs its testnet status."""
        adapter = BinanceSpotAdapter(network_config=NetworkConfig.testnet())

        # Trigger logging method if it exists
        if hasattr(adapter, "_log_testnet_status") and callable(adapter._log_testnet_status):
            adapter._log_testnet_status()

            # Should log about testnet URLs
            assert mock_log_info.call_count > 0
            # At least one log message should contain "testnet"
            any_testnet_log = False
            for call_args in mock_log_info.call_args_list:
                args, _ = call_args
                for arg in args:
                    if isinstance(arg, str) and "testnet" in arg.lower():
                        any_testnet_log = True
                        break
            assert any_testnet_log

    def test_network_config_overrides(self):
        """Test handling of network config with specific endpoint overrides."""
        # Create a config with only certain endpoints using testnet
        overrides = {
            EndpointType.CANDLES: NetworkEnvironment.TESTNET,
            EndpointType.TICKER: NetworkEnvironment.TESTNET,
            EndpointType.TRADES: NetworkEnvironment.PRODUCTION,
            EndpointType.ORDERS: NetworkEnvironment.PRODUCTION,
            EndpointType.ACCOUNT: NetworkEnvironment.PRODUCTION,
        }
        config = NetworkConfig(
            default_environment=NetworkEnvironment.PRODUCTION, endpoint_overrides=overrides
        )

        adapter = BinanceSpotAdapter(network_config=config)

        # Should use testnet for candles
        assert adapter._get_rest_url() == f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_ws_url() == SPOT_TESTNET_WSS_URL

    def test_for_testing_config(self):
        """Test that for_testing configuration forces production URLs."""
        config = NetworkConfig.for_testing()
        adapter = BinanceSpotAdapter(network_config=config)

        # Should always return production URLs
        assert adapter._get_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        assert adapter._get_ws_url() == SPOT_WSS_URL
