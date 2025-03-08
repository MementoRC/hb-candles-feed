"""
Unit tests for the BybitPerpetualAdapter class.
"""

import pytest

from candles_feed.adapters.bybit.constants import (
    CANDLES_ENDPOINT,
    PERP_WSS_URL,
    REST_URL,
)
from candles_feed.adapters.bybit.perpetual_adapter import BybitPerpetualAdapter


class TestBybitPerpetualAdapter:
    """Test suite for the BybitPerpetualAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = BybitPerpetualAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert BybitPerpetualAdapter.get_rest_url() == f"{REST_URL}{CANDLES_ENDPOINT}"

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert BybitPerpetualAdapter.get_ws_url() == PERP_WSS_URL

    def test_get_category_param(self):
        """Test category param retrieval."""
        assert self.adapter.get_category_param() == "linear"
