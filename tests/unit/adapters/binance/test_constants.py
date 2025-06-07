"""
Unit tests for Binance adapter constants.

Tests that necessary constants are defined and have appropriate values.
"""

from candles_feed.adapters.binance.constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_TESTNET_REST_URL,
    PERPETUAL_TESTNET_WSS_URL,
    PERPETUAL_WSS_URL,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_TESTNET_REST_URL,
    SPOT_TESTNET_WSS_URL,
    SPOT_WSS_URL,
)


class TestBinanceConstants:
    """Test suite for Binance adapter constants."""

    def test_spot_constants_exist(self):
        """Test that all required spot constants are defined."""
        assert SPOT_REST_URL is not None
        assert SPOT_WSS_URL is not None
        assert SPOT_CANDLES_ENDPOINT is not None
        assert SPOT_TESTNET_REST_URL is not None
        assert SPOT_TESTNET_WSS_URL is not None

    def test_perpetual_constants_exist(self):
        """Test that all required perpetual constants are defined."""
        assert PERPETUAL_REST_URL is not None
        assert PERPETUAL_WSS_URL is not None
        assert PERPETUAL_CANDLES_ENDPOINT is not None
        assert PERPETUAL_TESTNET_REST_URL is not None
        assert PERPETUAL_TESTNET_WSS_URL is not None

    def test_spot_url_formats(self):
        """Test that spot URLs have the expected format."""
        assert SPOT_REST_URL.startswith("https://")
        assert SPOT_WSS_URL.startswith("wss://")
        assert SPOT_TESTNET_REST_URL.startswith("https://")
        assert SPOT_TESTNET_WSS_URL.startswith("wss://")

    def test_perpetual_url_formats(self):
        """Test that perpetual URLs have the expected format."""
        assert PERPETUAL_REST_URL.startswith("https://")
        assert PERPETUAL_WSS_URL.startswith("wss://")
        assert PERPETUAL_TESTNET_REST_URL.startswith("https://")
        assert PERPETUAL_TESTNET_WSS_URL.startswith("wss://")

    def test_testnet_urls_differ_from_production(self):
        """Test that testnet URLs are different from production URLs."""
        # Spot URLs should be different
        assert SPOT_REST_URL != SPOT_TESTNET_REST_URL
        assert SPOT_WSS_URL != SPOT_TESTNET_WSS_URL

        # Perpetual URLs should be different
        assert PERPETUAL_REST_URL != PERPETUAL_TESTNET_REST_URL
        assert PERPETUAL_WSS_URL != PERPETUAL_TESTNET_WSS_URL

    def test_testnet_urls_contain_testnet(self):
        """Test that testnet URLs contain 'testnet' in their name."""
        # Check spot testnet URLs
        assert "testnet" in SPOT_TESTNET_REST_URL.lower()
        assert "testnet" in SPOT_TESTNET_WSS_URL.lower()

        # Check perpetual testnet URLs
        assert "testnet" in PERPETUAL_TESTNET_REST_URL.lower()
