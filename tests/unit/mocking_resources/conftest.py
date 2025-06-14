"""
Pytest fixtures for testing the mock exchange server components.
"""

import pytest

from candles_feed import CandleData
from candles_feed.mocking_resources.core import ExchangeType, create_mock_server


@pytest.fixture
def sample_candle():
    """Create a sample candle data object for testing."""
    return CandleData(
        timestamp_raw=1613677200,  # 2021-02-19 00:00:00 UTC
        open=50000.0,
        high=50500.0,
        low=49500.0,
        close=50200.0,
        volume=10.0,
        quote_asset_volume=500000.0,
        n_trades=100,
        taker_buy_base_volume=5.0,
        taker_buy_quote_volume=250000.0,
    )


@pytest.fixture
def sample_candles():
    """Create a list of sample candle data objects for testing."""
    candles = []
    base_timestamp = 1613677200  # 2021-02-19 00:00:00 UTC

    candles.extend(
        CandleData(
            timestamp_raw=base_timestamp + (i * 60),  # 1-minute intervals
            open=50000.0 + (i * 100),
            high=50500.0 + (i * 100),
            low=49500.0 + (i * 100),
            close=50200.0 + (i * 100),
            volume=10.0 + i,
            quote_asset_volume=(10.0 + i) * (50200.0 + (i * 100)),
            n_trades=100 + (i * 10),
            taker_buy_base_volume=5.0 + (i * 0.5),
            taker_buy_quote_volume=(5.0 + (i * 0.5)) * (50200.0 + (i * 100)),
        )
        for i in range(5)
    )
    return candles


@pytest.fixture
async def binance_mock_server():
    """Create and start a Binance mock server for testing."""
    server = create_mock_server(
        exchange_type=ExchangeType.BINANCE_SPOT, host="127.0.0.1", port=8080
    )

    if server is None:
        pytest.skip("Failed to create Binance mock server")

    # Add some trading pairs
    server.add_trading_pair("BTCUSDT", "1m", 50000.0)
    server.add_trading_pair("ETHUSDT", "1m", 3000.0)

    # Start the server
    await server.start()

    yield server

    # Clean up
    await server.stop()


# @pytest.fixture
# def event_loop():
#     """Create an event loop for each test."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()
