"""
Mock exchange server implementation for testing the candles feed package.

This module provides a modular framework for simulating cryptocurrency exchange APIs
(both REST and WebSocket) for integration and end-to-end testing without connecting
to real exchanges.
"""

from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType
from candles_feed.testing_resources.mocks.core.candle_data import MockCandleData
from candles_feed.testing_resources.mocks.core.factory import create_mock_server
