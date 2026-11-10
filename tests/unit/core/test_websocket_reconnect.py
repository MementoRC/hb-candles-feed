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
NOW = "candles_feed.core.collection_strategies.time.time"


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

    with sleep_patch, patch(NOW, return_value=T + 150):
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

    with sleep_patch, patch(NOW, return_value=T + 100):
        await strategy._listen_for_updates()

    assert events == ["rest:None", "subscribe", f"rest:{T}", "message"]
    assert [c.timestamp for c in candles_store] == [T, T + 60]


async def test_large_gap_replaces_store_with_newest_candles(strategy, mock_adapter):
    strategy._candles = deque([candle(T - 240 + 60 * i) for i in range(5)], maxlen=5)
    newest = [candle(T + 595 * 60 + 60 * i) for i in range(5)]
    mock_adapter.fetch_rest_candles.return_value = newest

    with patch(NOW, return_value=T + 600 * 60):
        await strategy._catch_up_candles()

    assert list(strategy._candles) == newest
    mock_adapter.fetch_rest_candles.assert_awaited_once()
    kwargs = mock_adapter.fetch_rest_candles.await_args.kwargs
    assert kwargs["start_time"] is None
    assert kwargs["limit"] == 5


async def test_catch_up_pages_until_open_candle(strategy, mock_adapter, candles_store):
    candles_store.append(candle(T))
    pages = {
        T: [candle(T), candle(T + 60), candle(T + 120)],
        T + 120: [candle(T + 120), candle(T + 180), candle(T + 240)],
    }

    async def fetch(**kwargs):
        return pages[kwargs["start_time"]]

    mock_adapter.fetch_rest_candles.side_effect = fetch

    # Mid-candle, so the T+240 candle is still open and no further page is requested
    with patch(NOW, return_value=T + 270):
        await strategy._catch_up_candles()

    assert [c.timestamp for c in candles_store] == [T, T + 60, T + 120, T + 180, T + 240]
    starts = [c.kwargs["start_time"] for c in mock_adapter.fetch_rest_candles.await_args_list]
    assert starts == [T, T + 120]


@pytest.mark.parametrize("page", [[], [candle(T)]])
async def test_catch_up_stops_when_page_has_nothing_new(
    strategy, mock_adapter, candles_store, page
):
    candles_store.append(candle(T))
    mock_adapter.fetch_rest_candles.return_value = page

    with patch(NOW, return_value=T + 600):
        await strategy._catch_up_candles()

    assert mock_adapter.fetch_rest_candles.await_count == 1
    assert [c.timestamp for c in candles_store] == [T]


async def test_ws_gap_triggers_rest_backfill_before_merge(
    strategy, mock_network_client, mock_adapter, make_ws, candles_store, sleep_stopper
):
    candles_store.append(candle(T))
    mock_adapter.parse_ws_message.return_value = [candle(T + 180)]
    fetches = 0

    async def fetch(**kwargs):
        # The post-subscribe catch-up finds nothing; the gap backfill finds the missing candles
        nonlocal fetches
        fetches += 1
        return [] if fetches == 1 else [candle(T + 60), candle(T + 120)]

    mock_adapter.fetch_rest_candles.side_effect = fetch
    mock_network_client.establish_ws_connection.return_value = make_ws(message_stream({"data": 1}))
    delays, sleep_patch = sleep_stopper(1)

    with sleep_patch, patch(NOW, return_value=T + 150):
        await strategy._listen_for_updates()

    starts = [c.kwargs["start_time"] for c in mock_adapter.fetch_rest_candles.await_args_list]
    assert starts == [T, T]  # post-subscribe catch-up, then the gap backfill
    assert [c.timestamp for c in candles_store] == [T, T + 60, T + 120, T + 180]


@pytest.mark.parametrize("offset", [0, 60])
async def test_ws_candle_without_gap_does_not_backfill(
    strategy, mock_network_client, mock_adapter, make_ws, candles_store, sleep_stopper, offset
):
    candles_store.append(candle(T))
    mock_adapter.parse_ws_message.return_value = [candle(T + offset)]
    mock_network_client.establish_ws_connection.return_value = make_ws(message_stream({"data": 1}))
    delays, sleep_patch = sleep_stopper(1)

    with sleep_patch, patch(NOW, return_value=T + 30):
        await strategy._listen_for_updates()

    # Only the post-subscribe catch-up; the message loop made no REST call
    assert mock_adapter.fetch_rest_candles.await_count == 1
    assert [c.timestamp for c in candles_store] == sorted({T, T + offset})


async def test_first_ws_candle_on_empty_store_initializes_before_merge(
    strategy, mock_network_client, mock_adapter, make_ws, sleep_stopper
):
    events: list[str] = []
    strategy._initialize_candles = AsyncMock(side_effect=lambda: events.append("init"))
    strategy._update_candles = MagicMock(side_effect=lambda _: events.append("merge"))
    mock_adapter.parse_ws_message.return_value = [candle(T)]
    mock_network_client.establish_ws_connection.return_value = make_ws(message_stream({"data": 1}))
    delays, sleep_patch = sleep_stopper(1)

    with sleep_patch:
        await strategy._listen_for_updates()

    # Startup init, post-subscribe init, then the init forced by the first message
    assert events == ["init", "init", "init", "merge"]


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

    with (
        sleep_patch,
        patch("candles_feed.core.collection_strategies.random.uniform", return_value=1.0),
    ):
        await strategy._listen_for_updates()

    mock_logger.warning.assert_called_once()
    ws.disconnect.assert_awaited_once()
    assert strategy._ws_assistant is None
    assert delays == [1.0]


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
