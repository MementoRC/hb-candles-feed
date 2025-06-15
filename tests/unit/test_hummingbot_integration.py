"""
Test the integration of the Candle Feed with Hummingbot components.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed import CandlesFeed, create_candles_feed_with_hummingbot
from candles_feed.mocking_resources.hummingbot.mock_components import (
    create_mock_hummingbot_components,
)


@pytest.fixture
def binance_rest_candles_response():
    """Sample Binance candles response for testing.

    :return: List of mock candle data in Binance format
    """
    return [
        # timestamp, open, high, low, close, volume, close_time, quote_volume, trades, taker_buy_volume, taker_buy_quote_volume, ignore
        [
            1625097600000,
            "35000.1",
            "35100.5",
            "34900.2",
            "35050.3",
            "10.5",
            1625097899999,
            "367000.5",
            100,
            "5.2",
            "182000.1",
            "0",
        ],
        [
            1625097900000,
            "35050.3",
            "35200.0",
            "35000.0",
            "35150.2",
            "12.3",
            1625098199999,
            "431500.2",
            120,
            "6.1",
            "214000.5",
            "0",
        ],
    ]


def create_mock_adapter():
    """Create a reusable mock adapter for tests."""
    mock_adapter = MagicMock()
    mock_adapter.get_trading_pair_format.return_value = "BTCUSDT"
    mock_adapter.get_rest_url.return_value = "https://api.binance.com/api/v3/klines"
    mock_adapter.get_ws_url.return_value = "wss://stream.binance.com/ws"
    mock_adapter.get_supported_intervals.return_value = {"1m": 60}
    mock_adapter.get_ws_supported_intervals.return_value = ["1m"]
    mock_adapter.get_rest_params.return_value = {}

    # Create a sample candle for the mock response
    from candles_feed.core.candle_data import CandleData

    sample_candle = CandleData(
        timestamp_raw=1625097600,
        open=35000.1,
        high=35100.5,
        low=34900.2,
        close=35050.3,
        volume=10.5,
        quote_asset_volume=350000.0,
        n_trades=100,
        taker_buy_base_volume=5.0,
        taker_buy_quote_volume=175000.0,
    )

    # Create AsyncMock for async methods
    mock_adapter.fetch_rest_candles = AsyncMock(return_value=[sample_candle])
    mock_adapter.parse_rest_response.return_value = [sample_candle]

    return mock_adapter


@pytest.fixture
def mock_hummingbot_components(binance_rest_candles_response):
    """Create mock Hummingbot components with pre-configured responses.

    :param binance_rest_candles_response: Mock response for Binance REST API
    :return: Dictionary with mock Hummingbot components
    """
    # Configure REST responses
    rest_responses = {
        "https://api.binance.com/api/v3/klines": binance_rest_candles_response,
    }

    # Configure WebSocket messages
    ws_messages = [
        json.dumps(
            {
                "e": "kline",
                "E": 1625098200000,
                "s": "BTCUSDT",
                "k": {
                    "t": 1625098200000,
                    "T": 1625098499999,
                    "s": "BTCUSDT",
                    "i": "1m",
                    "f": 12345,
                    "L": 12400,
                    "o": "35150.2",
                    "c": "35200.1",
                    "h": "35250.0",
                    "l": "35100.0",
                    "v": "15.2",
                    "n": 150,
                    "x": False,
                    "q": "534500.5",
                    "V": "7.5",
                    "Q": "263500.2",
                    "B": "0",
                },
            }
        )
    ]

    return create_mock_hummingbot_components(rest_responses=rest_responses, ws_messages=ws_messages)


@pytest.mark.asyncio
async def test_create_candles_feed_with_hummingbot(mock_hummingbot_components):
    """Test creating a CandlesFeed with Hummingbot components.

    :param mock_hummingbot_components: Mock Hummingbot components for testing
    """
    # Set up complete patching to avoid import errors
    with (
        patch("candles_feed.integration.HUMMINGBOT_AVAILABLE", True),
        patch("candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True),
        patch.dict(
            "sys.modules",
            {
                "hummingbot": MagicMock(),
                "hummingbot.core": MagicMock(),
                "hummingbot.core.api_throttler": MagicMock(),
                "hummingbot.core.api_throttler.async_throttler_base": MagicMock(),
                "hummingbot.core.web_assistant": MagicMock(),
                "hummingbot.core.web_assistant.web_assistants_factory": MagicMock(),
                "hummingbot.core.web_assistant.rest_assistant": MagicMock(),
                "hummingbot.core.web_assistant.ws_assistant": MagicMock(),
            },
        ),
        patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=create_mock_adapter(),
        ),
    ):
        # Create CandlesFeed with mock components
        feed = create_candles_feed_with_hummingbot(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            throttler=mock_hummingbot_components["throttler"],
            web_assistants_factory=mock_hummingbot_components["web_assistants_factory"],
        )

        # Verify the feed was created with the right components
        assert isinstance(feed, CandlesFeed)
        assert feed.exchange == "binance_spot"
        assert feed.trading_pair == "BTC-USDT"
        assert feed._hummingbot_components is not None
        assert feed._hummingbot_components["throttler"] == mock_hummingbot_components["throttler"]
        assert (
            feed._hummingbot_components["web_assistants_factory"]
            == mock_hummingbot_components["web_assistants_factory"]
        )


@pytest.mark.asyncio
async def test_candles_feed_rest_with_hummingbot(mock_hummingbot_components):
    """Test fetching candles with Hummingbot REST integration.

    :param mock_hummingbot_components: Mock Hummingbot components for testing
    """
    # Set up complete patching to avoid import errors
    with (
        patch("candles_feed.integration.HUMMINGBOT_AVAILABLE", True),
        patch("candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True),
        patch.dict(
            "sys.modules",
            {
                "hummingbot": MagicMock(),
                "hummingbot.core": MagicMock(),
                "hummingbot.core.api_throttler": MagicMock(),
                "hummingbot.core.api_throttler.async_throttler_base": MagicMock(),
                "hummingbot.core.web_assistant": MagicMock(),
                "hummingbot.core.web_assistant.web_assistants_factory": MagicMock(),
                "hummingbot.core.web_assistant.rest_assistant": MagicMock(),
                "hummingbot.core.web_assistant.ws_assistant": MagicMock(),
            },
        ),
        patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=create_mock_adapter(),
        ),
    ):
        # Create CandlesFeed with mock components
        feed = create_candles_feed_with_hummingbot(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            throttler=mock_hummingbot_components["throttler"],
            web_assistants_factory=mock_hummingbot_components["web_assistants_factory"],
        )

        # Patch the get_rest_data method of NetworkClientFactory.create_client
        with patch(
            "candles_feed.core.hummingbot_network_client_adapter.HummingbotNetworkClient.get_rest_data",
            new_callable=AsyncMock,
        ) as mock_get_rest_data:
            # Configure the mock to return the sample data
            mock_get_rest_data.return_value = mock_hummingbot_components[
                "web_assistants_factory"
            ].rest_connection.responses.get("https://api.binance.com/api/v3/klines")

            # Create a REST strategy with our mocked client
            feed._rest_strategy = feed._create_rest_strategy()

            # Fetch historical candles
            candles = await feed._rest_strategy.poll_once()

            # Verify we got the expected candles
            assert len(candles) == 1  # May be different depending on mock responses
            assert candles[0].timestamp == 1625097600
            assert candles[0].open == 35000.1
            assert candles[0].close == 35050.3


@pytest.mark.asyncio
async def test_candles_feed_ws_with_hummingbot(mock_hummingbot_components):
    """Test WebSocket connection with Hummingbot integration.

    :param mock_hummingbot_components: Mock Hummingbot components for testing
    """
    # Set up complete patching to avoid import errors
    with (
        patch("candles_feed.integration.HUMMINGBOT_AVAILABLE", True),
        patch("candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True),
        patch.dict(
            "sys.modules",
            {
                "hummingbot": MagicMock(),
                "hummingbot.core": MagicMock(),
                "hummingbot.core.api_throttler": MagicMock(),
                "hummingbot.core.api_throttler.async_throttler_base": MagicMock(),
                "hummingbot.core.web_assistant": MagicMock(),
                "hummingbot.core.web_assistant.web_assistants_factory": MagicMock(),
                "hummingbot.core.web_assistant.rest_assistant": MagicMock(),
                "hummingbot.core.web_assistant.ws_assistant": MagicMock(),
            },
        ),
        patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=create_mock_adapter(),
        ),
    ):
        # Create CandlesFeed with mock components
        feed = create_candles_feed_with_hummingbot(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            throttler=mock_hummingbot_components["throttler"],
            web_assistants_factory=mock_hummingbot_components["web_assistants_factory"],
        )

        # Mock WebSocketStrategy._listen_for_updates to avoid network calls
        with patch(
            "candles_feed.core.collection_strategies.WebSocketStrategy._listen_for_updates",
            new_callable=AsyncMock,
        ) as mock_listen:
            # Start the feed with websocket strategy
            await feed.start(strategy="websocket")

            # Verify the websocket strategy was created and started
            assert feed._ws_strategy is not None
            assert feed._using_ws is True
            assert mock_listen.called

            # Clean up
            await feed.stop()
