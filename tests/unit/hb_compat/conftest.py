"""Shared fixtures for hb_compat tests."""

from unittest.mock import MagicMock, patch

import pytest

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry


@pytest.fixture(autouse=True)
def mock_exchange_registry():
    """Mock ExchangeRegistry for all hb_compat tests.

    CandlesFeed.__init__ calls ExchangeRegistry.get_adapter_instance() immediately,
    so this must be mocked before any CandlesBaseAdapter is constructed.
    """
    with patch.object(ExchangeRegistry, "get_adapter_instance") as mock:
        mock_adapter = MagicMock(spec=BaseAdapter)
        mock_adapter.get_trading_pair_format.return_value = "BTCUSDT"
        mock_adapter.get_supported_intervals.return_value = {
            "1m": 60, "5m": 300, "15m": 900, "1h": 3600,
        }
        mock_adapter.get_ws_supported_intervals.return_value = ["1m", "5m", "1h"]
        mock.return_value = mock_adapter
        yield mock


@pytest.fixture(autouse=True)
def mock_network_client_factory():
    """Mock NetworkClientFactory to prevent real network client creation."""
    with patch(
        "candles_feed.core.hummingbot_network_client_adapter.NetworkClientFactory.create_client"
    ) as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock
