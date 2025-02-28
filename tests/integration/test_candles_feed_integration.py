"""
Integration tests for the CandlesFeed framework.

These tests verify that the CandlesFeed component works correctly with
actual adapter implementations, without making real API calls.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.adapters.binance_spot.binance_spot_adapter import BinanceSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.network_client import NetworkClient


class TestCandlesFeedIntegration:
    """Integration test suite for the CandlesFeed class."""

    @pytest.fixture
    def mock_rest_response(self):
        """Create a mock REST API response."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000  # Binance uses ms

        return [
            [
                base_time,
                "50000.0",
                "51000.0",
                "49000.0",
                "50500.0",
                "100.0",
                base_time + 59999,
                "5000000.0",
                1000,
                "60.0",
                "3000000.0",
                "0"
            ],
            [
                base_time + 60000,
                "50500.0",
                "52000.0",
                "50000.0",
                "51500.0",
                "150.0",
                base_time + 119999,
                "7500000.0",
                1500,
                "90.0",
                "4500000.0",
                "0"
            ]
        ]

    @pytest.fixture
    def mock_ws_message(self):
        """Create a mock WebSocket message."""
        base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000  # Binance uses ms

        return {
            "e": "kline",
            "E": base_time + 100,
            "s": "BTCUSDT",
            "k": {
                "t": base_time,
                "T": base_time + 59999,
                "s": "BTCUSDT",
                "i": "1m",
                "f": 100,
                "L": 200,
                "o": "50000.0",
                "c": "50500.0",
                "h": "51000.0",
                "l": "49000.0",
                "v": "100.0",
                "n": 1000,
                "x": False,
                "q": "5000000.0",
                "V": "60.0",
                "Q": "3000000.0",
                "B": "0"
            }
        }

    @pytest.fixture
    def mock_network_client(self, mock_rest_response, mock_ws_message):
        """Create a mocked NetworkClient that returns predefined responses."""
        client = MagicMock(spec=NetworkClient)

        # Setup the REST response
        client.get_rest_data = AsyncMock(return_value=mock_rest_response)

        # Setup the WebSocket
        ws_assistant = MagicMock()
        ws_assistant.connect = AsyncMock()
        ws_assistant.disconnect = AsyncMock()
        ws_assistant.send = AsyncMock()

        # Create a generator that will yield the mock WebSocket message
        async def mock_iter_messages():
            for _ in range(2):  # Yield two messages
                yield mock_ws_message
                await asyncio.sleep(0.1)

        ws_assistant.iter_messages = mock_iter_messages
        client.establish_ws_connection = AsyncMock(return_value=ws_assistant)

        return client

    @pytest.mark.asyncio
    async def test_rest_strategy_integration(self, mock_network_client):
        """Test the integration of CandlesFeed with REST strategy."""
        # Create the feed with a mocked network client
        with patch('candles_feed.core.candles_feed.NetworkClient', return_value=mock_network_client):
            feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100
            )

            # Start the feed with REST polling strategy
            await feed.start(strategy="polling")

            # Verify the REST client was called with appropriate parameters
            mock_network_client.get_rest_data.assert_called_once()

            # Wait a moment for the feed to process data
            await asyncio.sleep(0.2)

            # Verify candles were added
            candles = feed.get_candles()
            assert len(candles) > 0

            # Stop the feed
            await feed.stop()

    @pytest.mark.asyncio
    async def test_websocket_strategy_integration(self, mock_network_client):
        """Test the integration of CandlesFeed with WebSocket strategy."""
        # Create the feed with a mocked network client
        with patch('candles_feed.core.candles_feed.NetworkClient', return_value=mock_network_client):
            feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100
            )

            # Start the feed with WebSocket strategy
            await feed.start(strategy="websocket")

            # Verify a WebSocket connection was established
            mock_network_client.establish_ws_connection.assert_called_once()

            # Wait for WebSocket messages to be processed
            await asyncio.sleep(0.3)

            # Verify candles were added from WebSocket
            candles = feed.get_candles()
            assert len(candles) > 0

            # Stop the feed
            await feed.stop()

    @pytest.mark.asyncio
    async def test_fetch_historical_candles(self, mock_network_client):
        """Test fetching historical candles."""
        # Create the feed with a mocked network client
        with patch('candles_feed.core.candles_feed.NetworkClient', return_value=mock_network_client):
            feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100
            )

            # Fetch historical candles
            await feed.fetch_candles()

            # Verify the REST client was called
            mock_network_client.get_rest_data.assert_called_once()

            # Verify candles were added
            candles = feed.get_candles()
            assert len(candles) == 2  # Two candles from our mock response
