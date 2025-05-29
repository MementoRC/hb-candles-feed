import asyncio
import logging
from collections import deque
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.adapters.protocols import AdapterProtocol
from candles_feed.core.candle_data import CandleData
from candles_feed.core.collection_strategies import RESTPollingStrategy, WebSocketStrategy
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.protocols import WSAssistant


@pytest.fixture
def mock_network_client():
    client = AsyncMock(NetworkClient)
    client.get_rest_data = AsyncMock()
    client.establish_ws_connection = AsyncMock()
    client.send_ws_message = AsyncMock()
    client.fetch_rest_candles = AsyncMock()
    return client


@pytest.fixture
def mock_adapter():
    adapter = MagicMock(AdapterProtocol)
    adapter.get_rest_url = MagicMock(return_value="test_rest_url")
    adapter.get_ws_url = MagicMock(return_value="test_ws_url")
    adapter.get_rest_params = MagicMock(return_value={})
    adapter.get_ws_subscription_payload = MagicMock(return_value={})
    adapter.parse_rest_response = MagicMock(return_value=[])
    adapter.parse_ws_message = MagicMock(return_value=[])
    adapter.get_supported_intervals = MagicMock(return_value={"1m": 60})
    adapter.fetch_rest_candles = AsyncMock()
    adapter.fetch_rest_candles_synchronous = MagicMock()
    return adapter


@pytest.fixture
def mock_data_processor():
    processor = MagicMock(DataProcessor)
    processor.sanitize_candles = MagicMock(side_effect=lambda candles, interval: candles)
    processor.process_candle = MagicMock()
    return processor


@pytest.fixture
def mock_ws_assistant():
    assistant = AsyncMock(WSAssistant)
    assistant.iter_messages = AsyncMock(return_value=AsyncMock(AsyncGenerator))
    return assistant


@pytest.fixture
def candles_store():
    return deque(maxlen=100)


@pytest.fixture
def mock_logger():
    return MagicMock(logging.Logger)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "candles, expected_candles",
    [
        (
            [],
            [],
        ),
        (
            [CandleData(1678886400, 1.0, 2.0, 0.5, 1.5, 100.0)],
            [CandleData(1678886400, 1.0, 2.0, 0.5, 1.5, 100.0)],
        ),
        (
            [
                CandleData(1678886400, 1.0, 2.0, 0.5, 1.5, 100.0),
                CandleData(1678890000, 1.5, 2.5, 1.0, 2.0, 150.0),
            ],
            [
                CandleData(1678886400, 1.0, 2.0, 0.5, 1.5, 100.0),
                CandleData(1678890000, 1.5, 2.5, 1.0, 2.0, 150.0),
            ],
        ),
    ],
    ids=["empty_candles", "single_candle", "multiple_candles"],
)
async def test_ws_strategy_poll_once(
    mock_network_client,
    mock_adapter,
    mock_data_processor,
    candles_store,
    mock_logger,
    candles,
    expected_candles,
):
    # Arrange
    mock_adapter.fetch_rest_candles = AsyncMock(return_value=candles)
    mock_adapter.get_supported_intervals = MagicMock(return_value={"1m": 60})
    mock_data_processor.sanitize_candles = MagicMock(return_value=expected_candles)

    # Act
    strategy = WebSocketStrategy(
        mock_network_client,
        mock_adapter,
        "BTC-USDT",
        "1m",
        mock_data_processor,
        candles_store,
        mock_logger,
    )
    result = await strategy.poll_once()

    # Assert
    assert result == expected_candles
    mock_adapter.fetch_rest_candles.assert_awaited_once_with(
        trading_pair="BTC-USDT",
        interval="1m",
        start_time=None,
        limit=None,
        network_client=mock_network_client,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id, initial_candles, expected_candles",
    [
        (
            "no_initial_candles",
            [],
            [],
        ),
        (
            "initial_candles",
            [CandleData(1, 1.0, 1.0, 1.0, 1.0, 1.0)],
            [CandleData(1, 1.0, 1.0, 1.0, 1.0, 1.0)],
        ),
    ],
    ids=[
        "no_initial_candles",
        "initial_candles",
    ],
)
async def test_listen_for_updates(
    test_id,
    mock_network_client,
    mock_adapter,
    mock_data_processor,
    candles_store,
    mock_logger,
    mock_ws_assistant,
    initial_candles,
    expected_candles,
):
    # Set up mocks for WebSocketStrategy methods
    initialize_candles_mock = AsyncMock()
    update_candles_mock = MagicMock()

    # Mock the ws connection and message sending
    mock_network_client.establish_ws_connection = AsyncMock(return_value=mock_ws_assistant)
    mock_network_client.send_ws_message = AsyncMock()

    # Add initial candles to the store
    for candle in initial_candles:
        candles_store.append(candle)

    # Create a simple class to mock the strategy
    class MockStrategy(WebSocketStrategy):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._running = True  # Set to True initially

        async def _initialize_candles(self):
            await initialize_candles_mock()

        def _update_candles(self, candles):
            update_candles_mock(candles)

    # Setup adapter mocks
    mock_adapter.get_ws_url = MagicMock(return_value="ws://test.url")
    mock_adapter.get_ws_subscription_payload = MagicMock(return_value={"subscribe": "test"})
    mock_adapter.get_supported_intervals = MagicMock(return_value={"1m": 60})
    mock_adapter.parse_ws_message = MagicMock(return_value=[CandleData(2, 2.0, 2.0, 2.0, 2.0, 2.0)])

    # Create strategy instance
    strategy = MockStrategy(
        mock_network_client,
        mock_adapter,
        "BTC-USDT",
        "1m",
        mock_data_processor,
        candles_store,
        mock_logger,
    )

    # If there are initial candles, set the ready event
    if initial_candles:
        strategy._ready_event.set()

    # Act - run the listen updates method for a short time
    listen_task = asyncio.create_task(strategy._listen_for_updates())

    # Set up mock for websocket communication
    mock_message = {"data": "test"}
    mock_ws_assistant.iter_messages = AsyncMock()
    mock_ws_assistant.iter_messages.__aiter__.return_value = mock_ws_assistant.iter_messages
    mock_ws_assistant.iter_messages.__anext__.side_effect = [mock_message, StopAsyncIteration()]

    # Wait for the task to process
    await asyncio.sleep(0.1)
    strategy._running = False  # Stop the listening loop
    await listen_task

    # Assert
    assert list(candles_store) == expected_candles

    # Verify the correct calls were made
    mock_network_client.establish_ws_connection.assert_awaited_once_with("ws://test.url")
    mock_network_client.send_ws_message.assert_awaited_once_with(
        mock_ws_assistant, {"subscribe": "test"}
    )

    # Check initialize_candles was called if necessary
    if not initial_candles:
        initialize_candles_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_initialize_candles_success(
    mock_network_client,
    mock_adapter,
    mock_data_processor,
    candles_store,
    mock_logger,
):
    # Arrange
    expected_candles = [CandleData(1, 1.0, 1.0, 1.0, 1.0, 1.0)] * 100
    mock_adapter.fetch_rest_candles = AsyncMock(return_value=expected_candles)
    mock_adapter.get_supported_intervals = MagicMock(return_value={"1m": 60})
    mock_data_processor.sanitize_candles = MagicMock(return_value=expected_candles)

    # Act
    strategy = WebSocketStrategy(
        mock_network_client,
        mock_adapter,
        "BTC-USDT",
        "1m",
        mock_data_processor,
        candles_store,
        mock_logger,
    )
    await strategy._initialize_candles()

    # Assert
    assert list(candles_store) == expected_candles
    assert strategy._ready_event.is_set()
    mock_adapter.fetch_rest_candles.assert_awaited_once_with(
        trading_pair="BTC-USDT",
        interval="1m",
        start_time=None,
        limit=candles_store.maxlen,
        network_client=mock_network_client,
    )


@pytest.mark.asyncio
async def test_initialize_candles_failure(
    mock_network_client,
    mock_adapter,
    mock_data_processor,
    candles_store,
    mock_logger,
):
    # Arrange
    mock_adapter.fetch_rest_candles = AsyncMock(return_value=[])  # Simulate no candles returned
    mock_adapter.get_supported_intervals = MagicMock(return_value={"1m": 60})
    mock_data_processor.sanitize_candles = MagicMock(return_value=[])

    # Act
    strategy = WebSocketStrategy(
        mock_network_client,
        mock_adapter,
        "BTC-USDT",
        "1m",
        mock_data_processor,
        candles_store,
        mock_logger,
    )
    await strategy._initialize_candles()

    # Assert
    assert len(candles_store) == 0
    assert not strategy._ready_event.is_set()
    mock_logger.warning.assert_called_once_with("Failed to initialize candles, will retry")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id, new_candles, expected_calls",
    [
        ("no_new_candles_ws", [], 0),
        (
            "single_new_candle_ws",
            [CandleData(1678886400, 1.0, 2.0, 0.5, 1.5, 100.0)],
            1,
        ),
        (
            "multiple_new_candles_ws",
            [
                CandleData(1678886400, 1.0, 2.0, 0.5, 1.5, 100.0),
                CandleData(1678890000, 1.5, 2.5, 1.0, 2.0, 150.0),
            ],
            2,
        ),
    ],
    ids=["no_new_candles_ws", "single_new_candle_ws", "multiple_new_candles_ws"],
)
async def test_update_candles_ws_strategy(
    mock_network_client,
    mock_adapter,
    mock_data_processor,
    candles_store,
    mock_logger,
    test_id,
    new_candles,
    expected_calls,
):
    # Act
    strategy = WebSocketStrategy(
        mock_network_client,
        mock_adapter,
        "BTC-USDT",
        "1m",
        mock_data_processor,
        candles_store,
        mock_logger,
    )

    strategy._update_candles(new_candles)

    # Assert
    assert mock_data_processor.process_candle.call_count == expected_calls

# These fixtures are already defined above, so we don't need to redefine them


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id, start_time, end_time, limit",
    [
        (
            "no_times_no_limit",
            None,
            None,
            None,
        ),
        (
            "start_time_only",
            1000,
            None,
            None,
        ),
        (
            "end_time_only",
            None,
            2000,
            None,
        ),
        (
            "limit_only",
            None,
            None,
            50,
        ),
        (
            "start_and_end_times",
            1000,
            2000,
            None,
        ),
        (
            "start_time_and_limit",
            1000,
            None,
            50,
        ),
        (
            "end_time_and_limit",
            None,
            2000,
            50,
        ),
        (
            "all_parameters",
            1000,
            2000,
            50,
        ),
    ],
    ids=[
        "no_times_no_limit",
        "start_time_only",
        "end_time_only",
        "limit_only",
        "start_and_end_times",
        "start_time_and_limit",
        "end_time_and_limit",
        "all_parameters",
    ],
)
@patch("candles_feed.core.collection_strategies.time")
async def test_rest_strategy_poll_once(
    mock_time,
    mock_network_client,
    mock_adapter,
    mock_data_processor,
    candles_store,
    mock_logger,
    test_id,
    start_time,
    end_time,
    limit,
):
    # Arrange
    mock_time.time = MagicMock(return_value=3000)  # Mocking time.time()
    expected_candles = [CandleData(1678886400, 1.0, 2.0, 0.5, 1.5, 100.0)]

    # Set up the adapter
    mock_adapter.get_supported_intervals = MagicMock(return_value={"1m": 60})
    mock_adapter.fetch_rest_candles = AsyncMock(return_value=expected_candles)

    # Set up data processor
    mock_data_processor.sanitize_candles = MagicMock(return_value=expected_candles)

    # Act
    strategy = RESTPollingStrategy(
        mock_network_client,
        mock_adapter,
        "BTC-USDT",
        "1m",
        mock_data_processor,
        candles_store,
        mock_logger,
    )
    result = await strategy.poll_once(start_time, end_time, limit)

    # Assert
    assert result == expected_candles

    # Calculate expected parameters based on the new implementation
    interval_seconds = 60
    expected_end_time = end_time if end_time is not None else 3000
    # Round down end_time to nearest interval
    expected_end_time = expected_end_time - (expected_end_time % interval_seconds)

    expected_start_time = start_time
    if expected_start_time is None and limit is not None:
        expected_start_time = expected_end_time - (limit * interval_seconds)
    elif expected_start_time is not None:
        expected_start_time = expected_start_time - (expected_start_time % interval_seconds)

    # Verify correct parameters were passed
    mock_adapter.fetch_rest_candles.assert_awaited_once_with(
        trading_pair="BTC-USDT",
        interval="1m",
        start_time=expected_start_time,
        limit=limit,
        network_client=mock_network_client,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id, initial_candles",
    [
        (
            "no_initial_candles",
            [],
        ),
        (
            "initial_candles",
            [CandleData(1, 1.0, 1.0, 1.0, 1.0, 1.0)],
        ),
    ],
    ids=["no_initial_candles", "initial_candles"],
)
@patch("candles_feed.core.collection_strategies.asyncio.sleep", new_callable=AsyncMock)
@patch("candles_feed.core.collection_strategies.time")
async def test_poll_for_updates(
    mock_time,
    mock_sleep,
    mock_network_client,
    mock_adapter,
    mock_data_processor,
    candles_store,
    mock_logger,
    test_id,
    initial_candles,
):
    """Test the _poll_for_updates method of the RESTPollingStrategy class.

    This test verifies:
    1. Initial fetching logic when candles_store is empty/non-empty
    2. Setting of the ready_event
    3. The incremental update logic based on last timestamp
    """
    # Set up initial test conditions
    mock_time.time.return_value = 3000
    mock_sleep.return_value = None
    mock_adapter.get_supported_intervals.return_value = {"1m": 60}

    # Add initial candles to the store if any
    for candle in initial_candles:
        candles_store.append(candle)

    # Create new candles that would be returned by poll_once
    initial_poll_result = [CandleData(2, 2.0, 2.0, 2.0, 2.0, 2.0)]
    incremental_poll_result = [CandleData(3, 3.0, 3.0, 3.0, 3.0, 3.0)]

    # Create a custom RESTPollingStrategy subclass with controlled behavior
    class TestRESTStrategy(RESTPollingStrategy):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.poll_once_calls = []
            self.update_candles_calls = []

        async def poll_once(self, start_time=None, end_time=None, limit=None):
            # Track calls to poll_once with their parameters
            self.poll_once_calls.append((start_time, end_time, limit))

            # Return different results based on when poll_once is called
            if not self.poll_once_calls or len(self.poll_once_calls) == 1:
                return initial_poll_result
            else:
                return incremental_poll_result

        def _update_candles(self, candles):
            # Track calls to _update_candles
            self.update_candles_calls.append(candles)

            # In the test, we'll manually update candles rather than
            # relying on the actual implementation
            if not initial_candles or len(self.update_candles_calls) > 1:
                for candle in candles:
                    self._candles.append(candle)

    # Create strategy with our test implementation
    strategy = TestRESTStrategy(
        mock_network_client,
        mock_adapter,
        "BTC-USDT",
        "1m",
        mock_data_processor,
        candles_store,
        mock_logger,
    )

    # Run the polling task for a short time
    strategy._running = True
    poll_task = asyncio.create_task(strategy._poll_for_updates())

    # Allow the task to process the initial fetch and at least one update
    # We use a counter with our mocked sleep to track loop iterations
    sleep_counter = 0

    async def count_sleep(*args, **kwargs):
        nonlocal sleep_counter
        sleep_counter += 1
        # Stop after two iterations
        if sleep_counter >= 2:
            strategy._running = False

    mock_sleep.side_effect = count_sleep

    # Wait for the task to complete
    await poll_task

    # Verify behavior based on test case
    # Common assertions for both test cases
    # 1. Ready event should be set
    assert strategy._ready_event.is_set()
    # 2. At least one call to poll_once should have been made
    assert len(strategy.poll_once_calls) >= 1

    if not initial_candles:
        # For empty initial store:
        # 1. First poll_once should be called with limit parameter
        assert strategy.poll_once_calls[0][2] == candles_store.maxlen
        # 2. We should have at least the initial candles in the store
        # Note: Due to the way our test is structured, we'll get both initial_poll_result
        # and incremental_poll_result candles, but the exact count may vary
        assert len(candles_store) >= len(initial_poll_result)
        # 3. Verify the candles in the store contain our expected candles
        assert any(c.timestamp == 2 for c in candles_store), "Initial poll candles not found"
    else:
        # For non-empty initial store:
        # 1. The store should still contain the original candle
        assert any(c.timestamp == 1 for c in candles_store), "Initial candle missing"
        # 2. First poll should use start_time of initial candle in incremental updates
        # The loop will call poll_once at least once after initialization
        if len(strategy.poll_once_calls) > 1:
            assert strategy.poll_once_calls[1][0] == 1, "Incremental poll should start from timestamp 1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id, new_candles, expected_calls",
    [
        ("no_new_candles_rest", [], 0),
        (
            "single_new_candle_rest",
            [CandleData(1678886400, 1.0, 2.0, 0.5, 1.5, 100.0)],
            1,
        ),
        (
            "multiple_new_candles_rest",
            [
                CandleData(1678886400, 1.0, 2.0, 0.5, 1.5, 100.0),
                CandleData(1678890000, 1.5, 2.5, 1.0, 2.0, 150.0),
            ],
            2,
        ),
    ],
    ids=["no_new_candles_rest", "single_new_candle_rest", "multiple_new_candles_rest"],
)
async def test_update_candles_rest_strategy(
    mock_network_client, mock_adapter, mock_data_processor, candles_store, mock_logger,
    test_id, new_candles, expected_calls
):
    # Act
    strategy = RESTPollingStrategy(
        mock_network_client,
        mock_adapter,
        "BTC-USDT",
        "1m",
        mock_data_processor,
        candles_store,
        mock_logger,
    )
    strategy._update_candles(new_candles)

    # Assert
    assert mock_data_processor.process_candle.call_count == expected_calls

