"""
Unit tests for the BinancePerpetualAdapter class.
"""

import pytest

from candles_feed.adapters.binance.constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)
from candles_feed.adapters.binance.perpetual_adapter import (
    BinancePerpetualAdapter,
)


class TestBinancePerpetualAdapter:
    """Test suite for the BinancePerpetualAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = BinancePerpetualAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        expected_url = f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"
        assert BinancePerpetualAdapter.get_rest_url() == expected_url

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert BinancePerpetualAdapter.get_ws_url() == PERPETUAL_WSS_URL
