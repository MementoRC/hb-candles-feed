"""
Tests for paginated CandlesFeed.get_historical_candles.

A fake exchange serves pages from an in-memory candle list through a stubbed
adapter.fetch_rest_candles, honouring start_time and limit, so the real
RESTPollingStrategy.fetch_rest_page path runs.
"""

import asyncio
from collections import deque
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core import candles_feed as candles_feed_module
from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed, HistoricalCandlesError
from candles_feed.core.collection_strategies import RESTPollingStrategy
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.rate_limiter import RateLimitedNetworkClient, RateLimitExceededError

HOUR = 3600
BASE = 472_222 * HOUR  # hour-aligned epoch


def _candle(ts: int) -> CandleData:
    return CandleData(
        timestamp_raw=ts,
        open=1.0,
        high=2.0,
        low=0.5,
        close=1.5,
        volume=10.0,
    )


def _month_start(year: int, month: int) -> int:
    return int(datetime(year, month, 1, tzinfo=UTC).timestamp())


class FakeExchange:
    """Serves pages from a candle list; records every adapter call."""

    def __init__(
        self,
        timestamps: list[int],
        overlap: bool = False,
        ignore_start: bool = False,
        fail_from: int | None = None,
        fail_first: int = 0,
        error: BaseException | None = None,
    ):
        self.timestamps = sorted(timestamps)
        self.overlap = overlap
        self.ignore_start = ignore_start
        self.fail_from = fail_from
        self.fail_first = fail_first
        self.error = error or RuntimeError("boom")
        self.calls: list[dict] = []
        self.clients: list[object] = []

    async def fetch_rest_candles(
        self, trading_pair=None, interval=None, start_time=None, limit=None, network_client=None
    ):
        self.calls.append({"start_time": start_time, "limit": limit})
        self.clients.append(network_client)
        if len(self.calls) <= self.fail_first:
            raise self.error
        if self.fail_from is not None and start_time is not None and start_time >= self.fail_from:
            raise self.error
        limit = limit or 500
        if self.ignore_start:
            page = self.timestamps[-limit:]
        else:
            lower = start_time if start_time is not None else 0
            page = [ts for ts in self.timestamps if ts >= lower][:limit]
            if self.overlap and page:
                earlier = [ts for ts in self.timestamps if ts < page[0]][-1:]
                page = earlier + page + page[:1]
        return [_candle(ts) for ts in page]


def _install(feed: CandlesFeed, exchange: FakeExchange):
    return patch.object(
        feed._adapter,
        "fetch_rest_candles",
        AsyncMock(side_effect=exchange.fetch_rest_candles),
        create=True,
    )


def _make_feed(interval: str, seconds: int, max_per_request: int) -> CandlesFeed:
    adapter = MagicMock(spec=BaseAdapter)
    adapter.get_trading_pair_format.return_value = "BTCUSDT"
    adapter.get_supported_intervals.return_value = {interval: seconds}
    adapter.MAX_CANDLES_PER_REQUEST = max_per_request
    with (
        patch.object(ExchangeRegistry, "get_adapter_instance", return_value=adapter),
        patch(
            "candles_feed.hb_compat.hummingbot_network_client_adapter."
            "NetworkClientFactory.create_client",
            return_value=MagicMock(),
        ),
    ):
        return CandlesFeed(exchange="binance_spot", trading_pair="BTC-USDT", interval=interval)


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch):
    monkeypatch.setattr(candles_feed_module, "HISTORICAL_RETRY_BASE_DELAY", 0, raising=False)


@pytest.fixture
def feed() -> CandlesFeed:
    return _make_feed("1h", HOUR, 1000)


class TestHistoricalPagination:
    async def test_three_pages_full_contiguous_series(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series)
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE + 17, series[-1] + 5)

        assert len(exchange.calls) == 3
        assert [c["limit"] for c in exchange.calls] == [1000, 1000, 1000]
        assert list(df["timestamp"]) == series
        assert df["timestamp"].is_unique
        assert df["timestamp"].is_monotonic_increasing
        assert df["timestamp"].iloc[0] == BASE
        assert df["timestamp"].iloc[-1] == series[-1]
        assert df.attrs["gaps"] == []

    async def test_overlapping_pages_are_deduplicated(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series, overlap=True)
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert df["timestamp"].is_unique
        assert list(df["timestamp"]) == series

    async def test_hole_in_exchange_data_is_skipped(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        available = [ts for i, ts in enumerate(series) if not 990 <= i < 1010]
        exchange = FakeExchange(available)
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert list(df["timestamp"]) == available
        assert df.attrs["gaps"] == [(series[989], series[1010])]

    async def test_adapter_ignoring_start_terminates(self, feed):
        latest = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(latest, ignore_start=True)
        end = latest[-1] + 100 * HOUR
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE, end)

        assert len(exchange.calls) <= 3
        assert list(df["timestamp"]) == latest[-1000:]

    async def test_monthly_interval_uses_calendar_page_starts(self):
        feed = _make_feed("1M", 30 * 86400, 12)
        months = [_month_start(2022 + i // 12, i % 12 + 1) for i in range(30)]
        exchange = FakeExchange(months)
        with _install(feed, exchange):
            df = await feed.get_historical_candles(months[0] + 86400, months[-1] + 86400)

        assert list(df["timestamp"]) == months
        assert [c["start_time"] for c in exchange.calls] == [
            _month_start(2022, 1),
            _month_start(2023, 1),
            _month_start(2024, 1),
        ]
        assert df.attrs["gaps"] == []

    async def test_empty_exchange_returns_empty_dataframe(self, feed):
        exchange = FakeExchange([])
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE, BASE + 10 * HOUR)

        assert df.empty
        assert len(exchange.calls) == 1
        assert df.attrs["gaps"] == []

    async def test_range_smaller_than_one_page_is_single_call(self, feed):
        series = [BASE + i * HOUR for i in range(10)]
        exchange = FakeExchange(series)
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert len(exchange.calls) == 1
        assert list(df["timestamp"]) == series

    async def test_candles_outside_range_are_dropped(self, feed):
        series = [BASE + i * HOUR for i in range(50)]
        exchange = FakeExchange(series)
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE + 10 * HOUR, BASE + 20 * HOUR)

        assert list(df["timestamp"]) == series[10:21]

    async def test_does_not_call_fetch_candles_or_fill_live_store(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series)
        with (
            _install(feed, exchange),
            patch.object(feed, "fetch_candles", new_callable=AsyncMock) as mock_fetch,
        ):
            await feed.get_historical_candles(BASE, series[-1])

        mock_fetch.assert_not_called()
        assert feed.get_candles() == []

    async def test_pagination_uses_rate_limited_client(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series)
        with _install(feed, exchange):
            await feed.get_historical_candles(BASE, series[-1])

        assert isinstance(feed._network_client, RateLimitedNetworkClient)
        assert exchange.clients
        assert all(c is feed._network_client for c in exchange.clients)


class TestHistoricalGaps:
    async def test_gap_inside_single_page_keeps_both_sides(self, feed):
        series = [BASE + i * HOUR for i in range(100)]
        available = [ts for i, ts in enumerate(series) if not 40 <= i < 45]
        exchange = FakeExchange(available)
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert len(exchange.calls) == 1
        assert list(df["timestamp"]) == available
        assert df.attrs["gaps"] == [(series[39], series[45])]

    async def test_gap_spanning_page_boundary_continues_past_it(self):
        feed = _make_feed("1h", HOUR, 100)
        series = [BASE + i * HOUR for i in range(300)]
        available = [ts for i, ts in enumerate(series) if not 100 <= i < 121]
        exchange = FakeExchange(available)
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert list(df["timestamp"]) == available
        assert df.attrs["gaps"] == [(series[99], series[121])]

    async def test_gaps_are_logged_once(self, feed):
        series = [BASE + i * HOUR for i in range(100)]
        available = [ts for i, ts in enumerate(series) if i not in (10, 30, 50)]
        exchange = FakeExchange(available)
        feed.logger = MagicMock()
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert len(df.attrs["gaps"]) == 3
        assert feed.logger.warning.call_count == 1


class TestHistoricalErrors:
    async def test_transient_error_is_retried(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series, fail_first=1)
        with _install(feed, exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert list(df["timestamp"]) == series
        assert len(exchange.calls) == 4  # 3 pages + 1 retry

    async def test_persistent_error_raises_with_partial(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series, fail_from=series[1000])
        with _install(feed, exchange), pytest.raises(HistoricalCandlesError) as excinfo:
            await feed.get_historical_candles(BASE, series[-1])

        err = excinfo.value
        assert err.failed_at == series[1000]
        assert list(err.partial["timestamp"]) == series[:1000]
        assert isinstance(err.__cause__, RuntimeError)
        page_two_attempts = [c for c in exchange.calls if c["start_time"] == series[1000]]
        assert len(page_two_attempts) == 3

    async def test_rate_limit_errors_do_not_use_up_attempts_or_sleep(self, feed, monkeypatch):
        # A huge retry delay would hang the test if rate-limit retries slept on top of the pause.
        monkeypatch.setattr(candles_feed_module, "HISTORICAL_RETRY_BASE_DELAY", 1000)
        series = [BASE + i * HOUR for i in range(10)]
        exchange = FakeExchange(series, fail_first=4, error=RateLimitExceededError(429))
        with _install(feed, exchange):
            df = await asyncio.wait_for(feed.get_historical_candles(BASE, series[-1]), 5)

        assert list(df["timestamp"]) == series
        assert len(exchange.calls) == 5  # 4 rate-limited + 1 success; more than 3 attempts

    async def test_persistent_rate_limit_gives_up_after_cap(self, feed, monkeypatch):
        monkeypatch.setattr(candles_feed_module, "HISTORICAL_RETRY_BASE_DELAY", 1000)
        exchange = FakeExchange([BASE], fail_first=100, error=RateLimitExceededError(418))
        with _install(feed, exchange), pytest.raises(HistoricalCandlesError) as excinfo:
            await asyncio.wait_for(feed.get_historical_candles(BASE, BASE + HOUR), 5)

        assert len(exchange.calls) == candles_feed_module.HISTORICAL_MAX_RATE_LIMIT_RETRIES
        assert isinstance(excinfo.value.__cause__, RateLimitExceededError)

    async def test_cancelled_error_is_not_retried(self, feed):
        exchange = FakeExchange([BASE], fail_first=1, error=asyncio.CancelledError())
        with _install(feed, exchange), pytest.raises(asyncio.CancelledError):
            await feed.get_historical_candles(BASE, BASE + HOUR)

        assert len(exchange.calls) == 1


def _strategy(adapter: MagicMock) -> RESTPollingStrategy:
    adapter.get_supported_intervals.return_value = {"1h": HOUR}
    return RESTPollingStrategy(
        network_client=MagicMock(),
        adapter=adapter,
        trading_pair="BTC-USDT",
        interval="1h",
        data_processor=DataProcessor(),
        candles_store=deque(maxlen=100),
    )


class TestLivePollOnceUnchanged:
    async def test_poll_once_still_sanitizes_to_longest_run(self):
        adapter = MagicMock(spec=BaseAdapter)
        run_a = [BASE + i * HOUR for i in range(10)]
        run_b = [BASE + (20 + i) * HOUR for i in range(3)]
        adapter.fetch_rest_candles = AsyncMock(return_value=[_candle(t) for t in run_a + run_b])
        strategy = _strategy(adapter)

        result = await strategy.poll_once(start_time=BASE, end_time=run_b[-1], limit=100)

        assert [c.timestamp for c in result] == run_a

    async def test_poll_once_swallows_adapter_exception(self):
        adapter = MagicMock(spec=BaseAdapter)
        adapter.fetch_rest_candles = AsyncMock(side_effect=RuntimeError("down"))
        strategy = _strategy(adapter)

        assert await strategy.poll_once(start_time=BASE, limit=10) == []

    async def test_fetch_rest_page_does_not_sanitize_or_swallow(self):
        adapter = MagicMock(spec=BaseAdapter)
        run_a = [BASE + i * HOUR for i in range(10)]
        run_b = [BASE + (20 + i) * HOUR for i in range(3)]
        adapter.fetch_rest_candles = AsyncMock(return_value=[_candle(t) for t in run_a + run_b])
        strategy = _strategy(adapter)

        page = await strategy.fetch_rest_page(start_time=BASE, limit=100)
        assert [c.timestamp for c in page] == run_a + run_b

        adapter.fetch_rest_candles = AsyncMock(side_effect=RuntimeError("down"))
        with pytest.raises(RuntimeError):
            await strategy.fetch_rest_page(start_time=BASE, limit=10)
