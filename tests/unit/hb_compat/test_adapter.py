"""Tests for CandlesBaseAdapter — the core translation layer."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from candles_feed.core.candle_data import CandleData


def _make_candle(ts: int, price: float = 100.0) -> CandleData:
    """Helper to create a CandleData with minimal fields."""
    return CandleData(
        timestamp_raw=ts,
        open=price,
        high=price + 1,
        low=price - 1,
        close=price + 0.5,
        volume=1000.0,
        quote_asset_volume=100000.0,
        n_trades=50,
        taker_buy_base_volume=500.0,
        taker_buy_quote_volume=50000.0,
    )


class TestCandlesBaseAdapterProperties:
    """Test property delegation to CandlesFeed."""

    def test_name_returns_exchange(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", interval="1m")
        assert adapter.name == "binance"

    def test_interval_delegation(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", interval="5m")
        assert adapter.interval == "5m"

    def test_max_records_delegation(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", max_records=1000)
        assert adapter.max_records == 1000

    def test_ready_delegation(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", max_records=2)
        assert adapter.ready is False
        adapter._feed.add_candle(_make_candle(1000))
        adapter._feed.add_candle(_make_candle(1060))
        assert adapter.ready is True

    def test_candles_df_is_property_not_method(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        df = adapter.candles_df
        assert isinstance(df, pd.DataFrame)

    def test_candles_df_has_correct_columns(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", max_records=2)
        adapter._feed.add_candle(_make_candle(1000))
        df = adapter.candles_df
        expected_columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_asset_volume",
            "n_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
        ]
        assert list(df.columns) == expected_columns

    def test_empty_candles_df_keeps_columns_and_float_dtype(self):
        from candles_feed.hb_compat.adapter import COLUMNS, CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        df = adapter.candles_df
        assert df.empty
        assert list(df.columns) == COLUMNS
        assert (df.dtypes == "float64").all()

    def test_non_empty_candles_df_is_all_float64_in_order(self):
        from candles_feed.hb_compat.adapter import COLUMNS, CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", max_records=2)
        adapter._feed.add_candle(_make_candle(1000))
        df = adapter.candles_df
        assert list(df.columns) == COLUMNS
        assert (df.dtypes == "float64").all()
        assert df["n_trades"].iloc[0] == 50.0

    def test_interval_in_seconds(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", interval="1m")
        assert adapter.interval_in_seconds == 60

    def test_get_exchange_trading_pair(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        result = adapter.get_exchange_trading_pair("BTC-USDT")
        assert isinstance(result, str)
        assert len(result) > 0


class TestCandlesBaseAdapterProtocolConformance:
    """Verify adapter satisfies CandlesBaseProtocol."""

    def test_isinstance_check(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        from candles_feed.hb_compat.protocols import CandlesBaseProtocol

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        assert isinstance(adapter, CandlesBaseProtocol)


class TestCandlesBaseAdapterLifecycle:
    """Test sync start/stop bridge."""

    async def test_start_schedules_async_task(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with patch.object(adapter._feed, "start", new_callable=AsyncMock) as mock_start:
            adapter.start()
            import asyncio

            await asyncio.sleep(0.1)
            mock_start.assert_called_once()

    async def test_start_task_exception_is_logged_not_dropped(self, caplog):
        import asyncio
        import logging

        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with (
            patch.object(
                adapter._feed, "start", new_callable=AsyncMock, side_effect=RuntimeError("boom-95")
            ),
            caplog.at_level(logging.ERROR),
        ):
            adapter.start()
            await asyncio.sleep(0.1)

        assert any(
            r.name.startswith("candles_feed")
            and r.levelno >= logging.ERROR
            and "boom-95" in r.getMessage() + str(r.exc_info)
            for r in caplog.records
        )

    async def test_stop_schedules_async_task(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with patch.object(adapter._feed, "stop", new_callable=AsyncMock) as mock_stop:
            adapter.stop()
            import asyncio

            await asyncio.sleep(0.1)
            mock_stop.assert_called_once()

    async def test_stop_before_start_does_not_raise(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        assert adapter.last_task_error is None
        with patch.object(adapter._feed, "stop", new_callable=AsyncMock) as mock_stop:
            adapter.stop()
            await asyncio.sleep(0.05)
            mock_stop.assert_called_once()

    async def test_duplicate_start_while_pending_is_ignored(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        gate = asyncio.Event()

        async def slow_start(*_a, **_k):
            await gate.wait()

        with patch.object(adapter._feed, "start", side_effect=slow_start) as mock_start:
            adapter.start()
            first = adapter._start_task
            adapter.start()
            assert adapter._start_task is first
            gate.set()
            await asyncio.sleep(0.05)
            assert mock_start.call_count == 1

    async def test_stop_cancels_pending_start(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        started_state = {"completed": False}

        async def slow_start(*_a, **_k):
            await asyncio.sleep(10)
            started_state["completed"] = True

        with (
            patch.object(adapter._feed, "start", side_effect=slow_start),
            patch.object(adapter._feed, "stop", new_callable=AsyncMock) as mock_stop,
        ):
            adapter.start()
            start_task = adapter._start_task
            await asyncio.sleep(0)
            adapter.stop()
            await asyncio.sleep(0.05)
            assert start_task.cancelled()
            assert not started_state["completed"]
            mock_stop.assert_called_once()
            assert adapter.last_task_error is None

    async def test_stop_task_reference_kept_and_exception_exposed(self, caplog):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with (
            patch.object(
                adapter._feed, "stop", new_callable=AsyncMock, side_effect=RuntimeError("boom-87")
            ),
            caplog.at_level(logging.ERROR),
        ):
            adapter.stop()
            assert isinstance(adapter._stop_task, asyncio.Task)
            await asyncio.sleep(0.05)

        assert any("boom-87" in r.getMessage() + str(r.exc_info) for r in caplog.records)
        assert isinstance(adapter.last_task_error, RuntimeError)
        assert "boom-87" in str(adapter.last_task_error)

    async def test_start_error_exposed(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with patch.object(
            adapter._feed, "start", new_callable=AsyncMock, side_effect=ValueError("bad")
        ):
            adapter.start()
            await asyncio.sleep(0.05)
        assert isinstance(adapter.last_task_error, ValueError)

    async def test_cancelled_task_not_reported_as_error(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")

        async def slow(*_a, **_k):
            await asyncio.sleep(10)

        with patch.object(adapter._feed, "start", side_effect=slow):
            adapter.start()
            await asyncio.sleep(0)
            adapter._start_task.cancel()
            await asyncio.sleep(0.05)
        assert adapter.last_task_error is None


class TestCandlesBaseAdapterDataConversion:
    """Test data format conversions."""

    async def test_fetch_candles_returns_ndarray(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        candles = [_make_candle(1000), _make_candle(1060)]
        with patch.object(
            adapter._feed, "fetch_candles", new_callable=AsyncMock, return_value=candles
        ):
            result = await adapter.fetch_candles(start_time=1000, end_time=1060)
            assert isinstance(result, np.ndarray)
            assert result.shape == (2, 10)
            # Validate full column values for first row match _make_candle(1000, 100.0)
            row = result[0]
            assert row[0] == 1000  # timestamp
            assert row[1] == 100.0  # open
            assert row[2] == 101.0  # high
            assert row[3] == 99.0  # low
            assert row[4] == 100.5  # close
            assert row[5] == 1000.0  # volume
            assert row[6] == 100000.0  # quote_asset_volume
            assert row[7] == 50  # n_trades
            assert row[8] == 500.0  # taker_buy_base_volume
            assert row[9] == 50000.0  # taker_buy_quote_volume

    async def test_fetch_candles_none_limit_defaults_to_exchange_max(self, mock_exchange_registry):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        mock_exchange_registry.return_value.MAX_CANDLES_PER_REQUEST = 1000
        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with patch.object(
            adapter._feed, "fetch_candles", new_callable=AsyncMock, return_value=[]
        ) as mock_fetch:
            await adapter.fetch_candles(start_time=1000, limit=None)
            mock_fetch.assert_called_once_with(start_time=1000, end_time=None, limit=1000)

    @pytest.mark.parametrize(
        ("limit", "expected"), [(5000, 1000), (1000, 1000), (250, 250), (1, 1), (0, 1), (-7, 1)]
    )
    async def test_fetch_candles_limit_clamped_to_1_and_exchange_max(
        self, mock_exchange_registry, limit, expected
    ):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        mock_exchange_registry.return_value.MAX_CANDLES_PER_REQUEST = 1000
        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with patch.object(
            adapter._feed, "fetch_candles", new_callable=AsyncMock, return_value=[]
        ) as mock_fetch:
            await adapter.fetch_candles(end_time=2000, limit=limit)
            mock_fetch.assert_called_once_with(start_time=None, end_time=2000, limit=expected)

    async def test_fetch_candles_both_times_none_raises(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with (
            patch.object(adapter._feed, "fetch_candles", new_callable=AsyncMock) as mock_fetch,
            pytest.raises(ValueError, match="Either the start time or end time must be specified."),
        ):
            await adapter.fetch_candles()
        mock_fetch.assert_not_called()

    @pytest.mark.parametrize("times", [{"start_time": 1000}, {"end_time": 2000}])
    async def test_fetch_candles_single_time_does_not_raise(self, times):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with patch.object(
            adapter._feed, "fetch_candles", new_callable=AsyncMock, return_value=[]
        ) as mock_fetch:
            await adapter.fetch_candles(**times)
        mock_fetch.assert_called_once()

    async def test_fetch_candles_does_not_mutate_candles_df(self, mock_exchange_registry):
        from candles_feed.core.candles_feed import CandlesFeed
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        adapter._feed.add_candle(_make_candle(500))
        before = adapter.candles_df.copy()
        fetched = [_make_candle(1000), _make_candle(1060)]
        strategy = MagicMock()
        strategy.poll_once = AsyncMock(return_value=fetched)
        with patch.object(CandlesFeed, "_create_rest_strategy", return_value=strategy):
            result = await adapter.fetch_candles(start_time=1000, end_time=1060)

        assert result.shape == (2, 10)
        pd.testing.assert_frame_equal(adapter.candles_df, before)
        assert len(adapter._feed.get_candles()) == 1

    async def test_get_historical_candles_unpacks_config(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        from candles_feed.hb_compat.data_types import HistoricalCandlesConfig

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        config = HistoricalCandlesConfig(
            connector_name="binance",
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=1000,
            end_time=2000,
        )
        mock_df = pd.DataFrame({"timestamp": [1000]})
        with patch.object(
            adapter._feed,
            "get_historical_candles",
            new_callable=AsyncMock,
            return_value=mock_df,
        ) as mock_hist:
            result = await adapter.get_historical_candles(config)
            mock_hist.assert_called_once_with(start_time=1000, end_time=2000)
            assert isinstance(result, pd.DataFrame)

    async def test_get_historical_candles_spans_multiple_pages(self, mock_exchange_registry):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        from candles_feed.hb_compat.data_types import HistoricalCandlesConfig

        mock_exchange_registry.return_value.MAX_CANDLES_PER_REQUEST = 100
        series = [60_000 + i * 60 for i in range(250)]
        calls = []

        async def fake_fetch(trading_pair=None, interval=None, start_time=None, limit=None, **_):
            calls.append(start_time)
            return [_make_candle(ts) for ts in series if ts >= start_time][:limit]

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", interval="1m")
        config = HistoricalCandlesConfig(
            connector_name="binance",
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=series[0],
            end_time=series[-1],
        )
        mock_exchange_registry.return_value.fetch_rest_candles = fake_fetch
        result = await adapter.get_historical_candles(config)

        assert len(calls) == 3
        assert len(result) == 250
        assert list(result["timestamp"]) == series
        assert result.attrs["gaps"] == []

    async def test_get_historical_candles_preserves_gaps_attr(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        from candles_feed.hb_compat.data_types import HistoricalCandlesConfig

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        config = HistoricalCandlesConfig(
            connector_name="binance",
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=1000,
            end_time=2000,
        )
        mock_df = pd.DataFrame({"timestamp": [1020, 1200]})
        mock_df.attrs["gaps"] = [(1020, 1200)]
        with patch.object(
            adapter._feed, "get_historical_candles", new_callable=AsyncMock, return_value=mock_df
        ):
            result = await adapter.get_historical_candles(config)

        assert result.attrs["gaps"] == [(1020, 1200)]

    async def test_get_historical_candles_propagates_historical_error(self):
        from candles_feed.core.candles_feed import HistoricalCandlesError
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        from candles_feed.hb_compat.data_types import HistoricalCandlesConfig

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        config = HistoricalCandlesConfig(
            connector_name="binance",
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=1000,
            end_time=2000,
        )
        error = HistoricalCandlesError("failed", partial=pd.DataFrame(), failed_at=1500)
        with (
            patch.object(
                adapter._feed, "get_historical_candles", new_callable=AsyncMock, side_effect=error
            ),
            pytest.raises(HistoricalCandlesError) as excinfo,
        ):
            await adapter.get_historical_candles(config)

        assert excinfo.value.failed_at == 1500

    async def test_get_historical_candles_empty_keeps_columns(self):
        from candles_feed.hb_compat.adapter import COLUMNS, CandlesBaseAdapter
        from candles_feed.hb_compat.data_types import HistoricalCandlesConfig

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        config = HistoricalCandlesConfig(
            connector_name="binance",
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=1000,
            end_time=2000,
        )
        with patch.object(
            adapter._feed,
            "get_historical_candles",
            new_callable=AsyncMock,
            return_value=pd.DataFrame(),
        ):
            result = await adapter.get_historical_candles(config)
        assert result.empty
        assert list(result.columns) == COLUMNS
        assert (result.dtypes == "float64").all()

    async def test_fetch_candles_empty_returns_empty_ndarray(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        with patch.object(adapter._feed, "fetch_candles", new_callable=AsyncMock, return_value=[]):
            result = await adapter.fetch_candles(start_time=1000, end_time=1060)
            assert isinstance(result, np.ndarray)
            assert result.shape == (0, 10)


class TestCandlesBaseAdapterResetWithDataFrame:
    """Test reset_with_dataframe for MarketDataProvider compatibility."""

    def test_reset_clears_and_repopulates(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", max_records=10)
        adapter._feed.add_candle(_make_candle(500))
        assert len(adapter._feed.get_candles()) == 1

        df = pd.DataFrame(
            [
                [1000, 100.0, 101.0, 99.0, 100.5, 1000.0, 100000.0, 50, 500.0, 50000.0],
                [1060, 101.0, 102.0, 100.0, 101.5, 1100.0, 110000.0, 55, 550.0, 55000.0],
            ],
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_asset_volume",
                "n_trades",
                "taker_buy_base_volume",
                "taker_buy_quote_volume",
            ],
        )
        adapter.reset_with_dataframe(df)

        candles = adapter._feed.get_candles()
        assert len(candles) == 2
        assert candles[0].timestamp == 1000
        assert candles[1].timestamp == 1060
        assert candles[0].open == 100.0
        assert candles[0].close == 100.5
        assert candles[0].volume == 1000.0
        assert candles[1].open == 101.0
        assert candles[1].close == 101.5
        assert candles[1].volume == 1100.0

    def test_reset_with_missing_optional_columns(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", max_records=10)
        df = pd.DataFrame(
            [
                [1000, 100.0, 101.0, 99.0, 100.5, 1000.0],
            ],
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        adapter.reset_with_dataframe(df)

        candles = adapter._feed.get_candles()
        assert len(candles) == 1
        assert candles[0].timestamp == 1000
        assert candles[0].open == 100.0
        assert candles[0].quote_asset_volume == 0.0
        assert candles[0].n_trades == 0
        assert candles[0].taker_buy_base_volume == 0.0
        assert candles[0].taker_buy_quote_volume == 0.0

    def test_reset_with_nan_optional_columns(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT", max_records=10)
        df = pd.DataFrame(
            [
                [
                    1000,
                    100.0,
                    101.0,
                    99.0,
                    100.5,
                    1000.0,
                    float("nan"),
                    float("nan"),
                    float("nan"),
                    float("nan"),
                ],
            ],
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "quote_asset_volume",
                "n_trades",
                "taker_buy_base_volume",
                "taker_buy_quote_volume",
            ],
        )
        adapter.reset_with_dataframe(df)

        candles = adapter._feed.get_candles()
        assert len(candles) == 1
        assert candles[0].open == 100.0
        assert candles[0].quote_asset_volume == 0.0
        assert candles[0].n_trades == 0
        assert candles[0].taker_buy_base_volume == 0.0
        assert candles[0].taker_buy_quote_volume == 0.0

    def test_reset_with_empty_dataframe(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        adapter = CandlesBaseAdapter(exchange="binance", trading_pair="BTC-USDT")
        adapter._feed.add_candle(_make_candle(500))

        adapter.reset_with_dataframe(pd.DataFrame())
        assert len(adapter._feed.get_candles()) == 0
