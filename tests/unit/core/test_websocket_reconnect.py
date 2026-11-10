"""Tests for WebSocketStrategy reconnect backoff, REST catch-up and inactivity watchdog."""

import asyncio
import logging
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.adapters.protocols import AdapterProtocol
from candles_feed.core.candle_data import CandleData
from candles_feed.core.collection_strategies import WebSocketStrategy
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.protocols import WSAssistant

T = 1_700_000_040  # multiple of 60


def candle(ts: int) -> CandleData:
    return CandleData(ts, 1.0, 2.0, 0.5, 1.5, 10.0)


def message_stream(*messages):
    """Return an async iterator yielding the given messages then ending."""

    async def gen():
        for message in messages:
            yield message

    return gen()


def hanging_stream():
    """Return an async iterator that never yields (a silent connection)."""

    async def gen():
        await asyncio.Event().wait()
        yield  # pragma: no cover

    return gen()


@pytest.fixture
def mock_network_client():
    client = AsyncMock(NetworkClient)
    client.establish_ws_connection = AsyncMock()
    client.send_ws_message = AsyncMock()
    return client


@pytest.fixture
def mock_adapter():
    adapter = MagicMock(AdapterProtocol)
    adapter.get_ws_url = MagicMock(return_value="ws://test.url")
    adapter.get_ws_subscription_payload = MagicMock(return_value={"subscribe": "test"})
    adapter.parse_ws_message = MagicMock(return_value=[])
    adapter.get_supported_intervals = MagicMock(return_value={"1m": 60})
    adapter.fetch_rest_candles = AsyncMock(return_value=[])
    return adapter


@pytest.fixture
def mock_logger():
    return MagicMock(logging.Logger)


@pytest.fixture
def candles_store():
    return deque(maxlen=100)


@pytest.fixture
def make_ws():
    def _make(*sessions):
        ws = AsyncMock(WSAssistant)
        ws.iter_messages = MagicMock(side_effect=list(sessions))
        return ws

    return _make


@pytest.fixture
def strategy(mock_network_client, mock_adapter, mock_logger, candles_store):
    strat = WebSocketStrategy(
        mock_network_client,
        mock_adapter,
        "BTC-USDT",
        "1m",
        DataProcessor(),
        candles_store,
        mock_logger,
    )
    strat._running = True
    return strat


@pytest.fixture
def sleep_stopper(strategy):
    """Patch asyncio.sleep to record delays and stop the strategy after N calls."""

    def _patch(stop_after: int):
        delays: list[float] = []

        async def fake_sleep(delay):
            delays.append(delay)
            if len(delays) >= stop_after:
                strategy._running = False

        return delays, patch(
            "candles_feed.core.collection_strategies.asyncio.sleep", side_effect=fake_sleep
        )

    return _patch


async def test_backoff_schedule_without_jitter(strategy):
    with patch("candles_feed.core.collection_strategies.random.uniform", return_value=1.0):
        delays = [strategy._next_reconnect_delay() for _ in range(7)]

    assert delays == [1, 2, 4, 8, 16, 30, 30]


async def test_backoff_first_delay_with_minimum_jitter(strategy):
    with patch("candles_feed.core.collection_strategies.random.uniform", return_value=0.5):
        assert strategy._next_reconnect_delay() == 0.5


async def test_backoff_huge_attempt_count_is_capped(strategy):
    strategy._reconnect_attempts = 10_000

    delay = strategy._next_reconnect_delay()

    assert delay <= WebSocketStrategy.RECONNECT_MAX_DELAY


async def test_backoff_resets_after_session_with_messages(
    strategy, mock_network_client, make_ws, candles_store, sleep_stopper
):
    candles_store.append(candle(T))
    strategy._reconnect_attempts = 3
    ws = make_ws(message_stream({"data": 1}))
    mock_network_client.establish_ws_connection.side_effect = [ws, ConnectionError("down")]
    delays, sleep_patch = sleep_stopper(2)

    with (
        sleep_patch,
        patch("candles_feed.core.collection_strategies.random.uniform", return_value=1.0),
    ):
        await strategy._listen_for_updates()

    # First session delivered a message -> attempts reset -> first delay is 1s, then 2s
    assert delays == [1.0, 2.0]


async def test_connection_errors_back_off_increasingly(
    strategy, mock_network_client, candles_store, sleep_stopper
):
    candles_store.append(candle(T))
    mock_network_client.establish_ws_connection.side_effect = ConnectionError("down")
    delays, sleep_patch = sleep_stopper(3)

    with (
        sleep_patch,
        patch("candles_feed.core.collection_strategies.random.uniform", return_value=1.0),
    ):
        await strategy._listen_for_updates()

    assert delays == [1.0, 2.0, 4.0]


async def test_reconnect_fills_gap_via_rest(
    strategy, mock_network_client, mock_adapter, make_ws, candles_store, sleep_stopper
):
    candles_store.append(candle(T))
    ws1 = make_ws(message_stream())
    ws2 = make_ws(message_stream())
    mock_network_client.establish_ws_connection.side_effect = [ws1, ws2]
    mock_adapter.fetch_rest_candles.side_effect = [
        [candle(T)],
        [candle(T), candle(T + 60), candle(T + 120)],
    ]
    delays, sleep_patch = sleep_stopper(2)

    with sleep_patch:
        await strategy._listen_for_updates()

    assert [c.timestamp for c in candles_store] == [T, T + 60, T + 120]
    assert mock_adapter.fetch_rest_candles.await_count == 2
    assert mock_adapter.fetch_rest_candles.await_args.kwargs["start_time"] == T


async def test_startup_gap_filled_after_first_subscribe(
    strategy, mock_network_client, mock_adapter, make_ws, candles_store, sleep_stopper
):
    events: list[str] = []

    async def fetch(**kwargs):
        events.append(f"rest:{kwargs['start_time']}")
        return [candle(T)] if kwargs["start_time"] is None else [candle(T), candle(T + 60)]

    def parse(message):
        events.append("message")
        return []

    mock_adapter.fetch_rest_candles.side_effect = fetch
    mock_adapter.parse_ws_message.side_effect = parse
    mock_network_client.send_ws_message.side_effect = lambda *_: events.append("subscribe")
    mock_network_client.establish_ws_connection.return_value = make_ws(message_stream({"data": 1}))
    delays, sleep_patch = sleep_stopper(1)

    with sleep_patch:
        await strategy._listen_for_updates()

    assert events == ["rest:None", "subscribe", f"rest:{T}", "message"]
    assert [c.timestamp for c in candles_store] == [T, T + 60]


async def test_inactivity_watchdog_raises_timeout(
    strategy, mock_network_client, mock_adapter, make_ws, candles_store
):
    candles_store.append(candle(T))
    mock_adapter.get_ws_inactivity_timeout = lambda: 0.05

    mock_network_client.establish_ws_connection.return_value = make_ws(hanging_stream())

    with pytest.raises(TimeoutError):
        await strategy._connect_and_listen()


async def test_inactivity_timeout_logs_disconnects_and_backs_off(
    strategy,
    mock_network_client,
    mock_adapter,
    mock_logger,
    make_ws,
    candles_store,
    sleep_stopper,
):
    candles_store.append(candle(T))
    mock_adapter.get_ws_inactivity_timeout = lambda: 0.05

    ws = make_ws(hanging_stream())
    mock_network_client.establish_ws_connection.return_value = ws
    delays, sleep_patch = sleep_stopper(1)

    with sleep_patch:
        await strategy._listen_for_updates()

    mock_logger.warning.assert_called_once()
    ws.disconnect.assert_awaited_once()
    assert strategy._ws_assistant is None
    assert len(delays) == 1


async def test_inactivity_hook_returning_none_disables_watchdog(strategy, mock_adapter):
    mock_adapter.get_ws_inactivity_timeout = lambda: None

    assert strategy._ws_inactivity_timeout() is None


@pytest.mark.parametrize(
    "interval, seconds, expected",
    [("1m", 60, 120.0), ("1s", 1, 60.0), ("1d", 86400, 600.0)],
)
async def test_default_inactivity_timeout(strategy, mock_adapter, interval, seconds, expected):
    mock_adapter.get_supported_intervals.return_value = {interval: seconds}
    strategy.interval = interval

    assert strategy._ws_inactivity_timeout() == expected
