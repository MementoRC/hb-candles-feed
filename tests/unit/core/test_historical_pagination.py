"""
Tests for paginated CandlesFeed.get_historical_candles.

A fake exchange serves pages from an in-memory candle list through a patched
RESTPollingStrategy.poll_once, honouring start_time and limit.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.collection_strategies import RESTPollingStrategy
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.rate_limiter import RateLimitedNetworkClient

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
    """Serves pages from a candle list; records every poll call."""

    def __init__(self, timestamps: list[int], overlap: bool = False, ignore_start: bool = False):
        self.timestamps = sorted(timestamps)
        self.overlap = overlap
        self.ignore_start = ignore_start
        self.calls: list[dict] = []
        self.strategies: list[RESTPollingStrategy] = []

    async def poll_once(self, strategy, start_time=None, end_time=None, limit=None):
        self.calls.append({"start_time": start_time, "end_time": end_time, "limit": limit})
        self.strategies.append(strategy)
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


def _install(exchange: FakeExchange):
    async def fake(self, start_time=None, end_time=None, limit=None):
        return await exchange.poll_once(self, start_time, end_time, limit)

    return patch.object(RESTPollingStrategy, "poll_once", fake)


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


@pytest.fixture
def feed() -> CandlesFeed:
    return _make_feed("1h", HOUR, 1000)


class TestHistoricalPagination:
    async def test_three_pages_full_contiguous_series(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series)
        with _install(exchange):
            df = await feed.get_historical_candles(BASE + 17, series[-1] + 5)

        assert len(exchange.calls) == 3
        assert [c["limit"] for c in exchange.calls] == [1000, 1000, 1000]
        assert list(df["timestamp"]) == series
        assert df["timestamp"].is_unique
        assert df["timestamp"].is_monotonic_increasing
        assert df["timestamp"].iloc[0] == BASE
        assert df["timestamp"].iloc[-1] == series[-1]

    async def test_overlapping_pages_are_deduplicated(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series, overlap=True)
        with _install(exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert df["timestamp"].is_unique
        assert list(df["timestamp"]) == series

    async def test_hole_in_exchange_data_is_skipped(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        available = [ts for i, ts in enumerate(series) if not 990 <= i < 1010]
        exchange = FakeExchange(available)
        with _install(exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert list(df["timestamp"]) == available

    async def test_adapter_ignoring_start_terminates(self, feed):
        latest = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(latest, ignore_start=True)
        end = latest[-1] + 100 * HOUR
        with _install(exchange):
            df = await feed.get_historical_candles(BASE, end)

        assert len(exchange.calls) <= 3
        assert list(df["timestamp"]) == latest[-1000:]

    async def test_monthly_interval_uses_calendar_page_starts(self):
        feed = _make_feed("1M", 30 * 86400, 12)
        months = [_month_start(2022 + i // 12, i % 12 + 1) for i in range(30)]
        exchange = FakeExchange(months)
        with _install(exchange):
            df = await feed.get_historical_candles(months[0] + 86400, months[-1] + 86400)

        assert list(df["timestamp"]) == months
        assert [c["start_time"] for c in exchange.calls] == [
            _month_start(2022, 1),
            _month_start(2023, 1),
            _month_start(2024, 1),
        ]

    async def test_empty_exchange_returns_empty_dataframe(self, feed):
        exchange = FakeExchange([])
        with _install(exchange):
            df = await feed.get_historical_candles(BASE, BASE + 10 * HOUR)

        assert df.empty
        assert len(exchange.calls) == 1

    async def test_range_smaller_than_one_page_is_single_call(self, feed):
        series = [BASE + i * HOUR for i in range(10)]
        exchange = FakeExchange(series)
        with _install(exchange):
            df = await feed.get_historical_candles(BASE, series[-1])

        assert len(exchange.calls) == 1
        assert list(df["timestamp"]) == series

    async def test_candles_outside_range_are_dropped(self, feed):
        series = [BASE + i * HOUR for i in range(50)]
        exchange = FakeExchange(series)
        with _install(exchange):
            df = await feed.get_historical_candles(BASE + 10 * HOUR, BASE + 20 * HOUR)

        assert list(df["timestamp"]) == series[10:21]

    async def test_does_not_call_fetch_candles_or_fill_live_store(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series)
        with (
            _install(exchange),
            patch.object(feed, "fetch_candles", new_callable=AsyncMock) as mock_fetch,
        ):
            await feed.get_historical_candles(BASE, series[-1])

        mock_fetch.assert_not_called()
        assert feed.get_candles() == []

    async def test_pagination_uses_rate_limited_client(self, feed):
        series = [BASE + i * HOUR for i in range(2500)]
        exchange = FakeExchange(series)
        with _install(exchange):
            await feed.get_historical_candles(BASE, series[-1])

        assert isinstance(feed._network_client, RateLimitedNetworkClient)
        assert exchange.strategies
        assert all(s.network_client is feed._network_client for s in exchange.strategies)
