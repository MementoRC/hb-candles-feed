"""
Testing resources for the candles feed package.

This module provides tools and utilities for testing the candles feed package in larger projects,
including mock exchange servers and fixtures.
"""

from candles_feed.mocking_resources.core import *
from candles_feed.mocking_resources.exchange_server_plugins import *
from candles_feed.mocking_resources.core.candle_data_factory import CandleDataFactory

# Import core components for easy access
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.server import MockedExchangeServer
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.factory import create_mock_server

__all__ = [
    "CandleDataFactory",
    "ExchangeType",
    "MockedExchangeServer",
    "ExchangePlugin",
    "create_mock_server",
]
