"""
Unit tests for the BybitPerpetualAdapter class.
"""

import pytest

from candles_feed.adapters.bybit.constants import PERP_WSS_URL
from candles_feed.adapters.bybit_perpetual.bybit_perpetual_adapter import BybitPerpetualAdapter


class TestBybitPerpetualAdapter:
    """Test suite for the BybitPerpetualAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = BybitPerpetualAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert self.adapter.get_ws_url() == PERP_WSS_URL
        
    def test_get_category_param(self):
        """Test category param retrieval."""
        assert self.adapter.get_category_param() == "linear"