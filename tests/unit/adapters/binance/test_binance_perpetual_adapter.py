"""
Unit tests for the BinancePerpetualAdapter class.
"""

import pytest

from candles_feed.adapters.binance.constants import (
    PERP_REST_URL,
    PERP_WSS_URL,
)
from candles_feed.adapters.binance.binance_perpetual_adapter import (
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
        assert self.adapter.get_rest_url() == PERP_REST_URL

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert self.adapter.get_ws_url() == PERP_WSS_URL
