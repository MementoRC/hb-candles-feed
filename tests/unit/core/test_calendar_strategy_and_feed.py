"""Calendar-aware 1w/1M handling in RESTPollingStrategy and CandlesFeed."""

import logging
from collections import deque
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.collection_strategies import RESTPollingStrategy
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.exchange_registry import ExchangeRegistry

INTERVALS = {"1m": 60, "1w": 604800, "1M": 2592000}


def _ts(year: int, month: int, day: int = 1) -> int:
    return int(datetime(year, month, day, tzinfo=UTC).timestamp())


def _dt(t: int) -> datetime:
    return datetime.fromtimestamp(t, UTC)


def _month_starts(n: int) -> list[int]:
    return [_ts(2023 + i // 12, i % 12 + 1) for i in range(n)]


def _candle(t: int) -> CandleData:
    return CandleData(t, 1.0, 2.0, 0.5, 1.5, 10.0)


def _strategy(interval: str, fetched: list[CandleData]):
    adapter = MagicMock()
    adapter.get_supported_intervals.return_value = INTERVALS
    adapter.fetch_rest_candles = AsyncMock(return_value=fetched)
    strategy = RESTPollingStrategy(
        MagicMock(),
        adapter,
        "BTC-USDT",
        interval,
        DataProcessor(),
        deque(maxlen=100),
        logging.getLogger("test"),
    )
    return strategy, adapter


@pytest.mark.asyncio
async def test_poll_once_monthly_window_and_full_series():
    stamps = _month_starts(13)
    strategy, adapter = _strategy("1M", [_candle(t) for t in stamps])
    end_time = _ts(2024, 1, 17) + 4321

    result = await strategy.poll_once(end_time=end_time, limit=12)

    start = adapter.fetch_rest_candles.await_args.kwargs["start_time"]
    assert start == _ts(2023, 1, 1)
    assert [c.timestamp for c in result] == stamps


@pytest.mark.asyncio
async def test_poll_once_monthly_explicit_start_floors_to_month():
    strategy, adapter = _strategy("1M", [])
    await strategy.poll_once(start_time=_ts(2023, 6, 14) + 99, end_time=_ts(2024, 1, 5))
    assert adapter.fetch_rest_candles.await_args.kwargs["start_time"] == _ts(2023, 6, 1)


@pytest.mark.asyncio
async def test_poll_once_weekly_start_is_monday():
    strategy, adapter = _strategy("1w", [])
    end_time = _ts(2023, 5, 4) + 5000  # Thursday

    await strategy.poll_once(end_time=end_time, limit=4)

    start = adapter.fetch_rest_candles.await_args.kwargs["start_time"]
    assert _dt(start).weekday() == 0
    assert start == _ts(2023, 4, 3)


@pytest.fixture
def feed_factory():
    def make(interval: str) -> CandlesFeed:
        adapter = MagicMock(spec=BaseAdapter)
        adapter.get_trading_pair_format.return_value = "BTC-USDT"
        adapter.get_supported_intervals.return_value = INTERVALS
        with patch.object(ExchangeRegistry, "get_adapter_instance", return_value=adapter):
            return CandlesFeed("binance_spot", "BTC-USDT", interval=interval, max_records=50)

    return make


def test_round_timestamp_monthly(feed_factory):
    feed = feed_factory("1M")
    assert feed._round_timestamp_to_interval_multiple(_ts(2023, 2, 20) + 77) == _ts(2023, 2, 1)


def test_round_timestamp_weekly_is_monday(feed_factory):
    feed = feed_factory("1w")
    for day in range(1, 8):
        rounded = feed._round_timestamp_to_interval_multiple(_ts(2023, 5, day) + 3600)
        assert _dt(rounded).weekday() == 0
        assert rounded == _ts(2023, 5, 1)


def test_round_timestamp_fixed_unchanged(feed_factory):
    feed = feed_factory("1m")
    assert feed._round_timestamp_to_interval_multiple(1_700_000_123) == 1_700_000_123 - 23


def test_equidistant_accepts_real_months(feed_factory):
    feed = feed_factory("1M")
    rows = [[t, 1, 2, 0.5, 1.5, 10] for t in _month_starts(13)]
    assert feed.check_candles_sorted_and_equidistant(rows) is True


def test_equidistant_rejects_missing_month(feed_factory):
    feed = feed_factory("1M")
    stamps = _month_starts(6)
    del stamps[2]
    rows = [[t, 1, 2, 0.5, 1.5, 10] for t in stamps]
    assert feed.check_candles_sorted_and_equidistant(rows) is False


def test_equidistant_weekly_monday_aligned(feed_factory):
    feed = feed_factory("1w")
    monday = _ts(2023, 5, 1)
    rows = [[monday + i * 604800, 1, 2, 0.5, 1.5, 10] for i in range(6)]
    assert feed.check_candles_sorted_and_equidistant(rows) is True
