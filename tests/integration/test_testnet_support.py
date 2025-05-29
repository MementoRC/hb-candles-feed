"""
Integration tests for testnet support.

This module tests that the testnet support works correctly with real exchanges.
"""

import asyncio
import logging

import pytest

from candles_feed import CandlesFeed
from candles_feed.core.network_config import EndpointType, NetworkConfig, NetworkEnvironment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="Requires network connection to Binance testnet")
@pytest.mark.asyncio
async def test_binance_testnet_rest():
    """Test that Binance testnet works with REST strategy."""
    # Create a feed with testnet configuration
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        network_config=NetworkConfig.testnet(),
        strategy="polling",
    )

    try:
        # Start the feed
        await feed.start()

        # Wait for some data to arrive
        await asyncio.sleep(5)

        # Verify we have candles
        candles = feed.get_candles()
        assert len(candles) > 0

        # Verify candle structure
        for candle in candles:
            assert candle.timestamp > 0
            assert candle.open >= 0
            assert candle.high >= candle.low
            assert candle.volume >= 0
    finally:
        # Ensure feed is stopped
        await feed.stop()


@pytest.mark.skip(reason="Requires network connection to Binance testnet")
@pytest.mark.asyncio
async def test_binance_testnet_ws():
    """Test that Binance testnet works with WebSocket strategy."""
    # Create a feed with testnet configuration
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        network_config=NetworkConfig.testnet(),
        strategy="websocket",
    )

    try:
        # Start the feed
        await feed.start()

        # Wait for some data to arrive
        await asyncio.sleep(5)

        # Verify we have candles
        candles = feed.get_candles()
        assert len(candles) > 0
    finally:
        # Ensure feed is stopped
        await feed.stop()


@pytest.mark.skip(reason="Requires network connection to Binance")
@pytest.mark.asyncio
async def test_binance_hybrid_mode():
    """Test that hybrid mode works correctly."""
    # Create a hybrid config that uses testnet for orders but production for candles
    config = NetworkConfig.hybrid(
        candles=NetworkEnvironment.PRODUCTION,
        orders=NetworkEnvironment.TESTNET,
    )

    # Verify the configuration is interpreted correctly
    assert config.is_testnet_for(EndpointType.ORDERS) is True
    assert config.is_testnet_for(EndpointType.CANDLES) is False

    # Create a feed with this configuration
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        network_config=config,
    )

    try:
        # Start the feed
        await feed.start()

        # Wait for some data to arrive
        await asyncio.sleep(5)

        # Verify we have candles (from production)
        candles = feed.get_candles()
        assert len(candles) > 0
    finally:
        # Ensure feed is stopped
        await feed.stop()
