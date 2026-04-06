"""Tests for CandlesBaseAdapter — the core translation layer."""

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
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT", interval="1m"
        )
        assert adapter.name == "binance"

    def test_interval_delegation(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT", interval="5m"
        )
        assert adapter.interval == "5m"

    def test_max_records_delegation(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT", max_records=1000
        )
        assert adapter.max_records == 1000

    def test_ready_delegation(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT", max_records=2
        )
        assert adapter.ready is False
        adapter._feed.add_candle(_make_candle(1000))
        adapter._feed.add_candle(_make_candle(1060))
        assert adapter.ready is True

    def test_candles_df_is_property_not_method(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
        df = adapter.candles_df
        assert isinstance(df, pd.DataFrame)

    def test_candles_df_has_correct_columns(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT", max_records=2
        )
        adapter._feed.add_candle(_make_candle(1000))
        df = adapter.candles_df
        expected_columns = [
            "timestamp", "open", "high", "low", "close", "volume",
            "quote_asset_volume", "n_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume",
        ]
        assert list(df.columns) == expected_columns

    def test_interval_in_seconds(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT", interval="1m"
        )
        assert adapter.interval_in_seconds == 60

    def test_get_exchange_trading_pair(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
        result = adapter.get_exchange_trading_pair("BTC-USDT")
        assert isinstance(result, str)
        assert len(result) > 0


class TestCandlesBaseAdapterProtocolConformance:
    """Verify adapter satisfies CandlesBaseProtocol."""

    def test_isinstance_check(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        from candles_feed.hb_compat.protocols import CandlesBaseProtocol
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
        assert isinstance(adapter, CandlesBaseProtocol)


class TestCandlesBaseAdapterLifecycle:
    """Test sync start/stop bridge."""

    @pytest.mark.asyncio
    async def test_start_schedules_async_task(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
        with patch.object(adapter._feed, "start", new_callable=AsyncMock) as mock_start:
            adapter.start()
            import asyncio
            await asyncio.sleep(0.1)
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_schedules_async_task(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
        with patch.object(adapter._feed, "stop", new_callable=AsyncMock) as mock_stop:
            adapter.stop()
            import asyncio
            await asyncio.sleep(0.1)
            mock_stop.assert_called_once()


class TestCandlesBaseAdapterDataConversion:
    """Test data format conversions."""

    @pytest.mark.asyncio
    async def test_fetch_candles_returns_ndarray(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
        candles = [_make_candle(1000), _make_candle(1060)]
        with patch.object(
            adapter._feed, "fetch_candles", new_callable=AsyncMock, return_value=candles
        ):
            result = await adapter.fetch_candles(start_time=1000, end_time=1060)
            assert isinstance(result, np.ndarray)
            assert result.shape == (2, 10)
            # Validate full column values for first row match _make_candle(1000, 100.0)
            row = result[0]
            assert row[0] == 1000        # timestamp
            assert row[1] == 100.0       # open
            assert row[2] == 101.0       # high
            assert row[3] == 99.0        # low
            assert row[4] == 100.5       # close
            assert row[5] == 1000.0      # volume
            assert row[6] == 100000.0    # quote_asset_volume
            assert row[7] == 50          # n_trades
            assert row[8] == 500.0       # taker_buy_base_volume
            assert row[9] == 50000.0     # taker_buy_quote_volume

    @pytest.mark.asyncio
    async def test_fetch_candles_none_limit_defaults_to_500(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
        with patch.object(
            adapter._feed, "fetch_candles", new_callable=AsyncMock, return_value=[]
        ) as mock_fetch:
            await adapter.fetch_candles(limit=None)
            mock_fetch.assert_called_once_with(
                start_time=None, end_time=None, limit=500
            )

    @pytest.mark.asyncio
    async def test_get_historical_candles_unpacks_config(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        from candles_feed.hb_compat.data_types import HistoricalCandlesConfig
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
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

    @pytest.mark.asyncio
    async def test_fetch_candles_empty_returns_empty_ndarray(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
        with patch.object(
            adapter._feed, "fetch_candles", new_callable=AsyncMock, return_value=[]
        ):
            result = await adapter.fetch_candles(start_time=1000, end_time=1060)
            assert isinstance(result, np.ndarray)
            assert result.shape == (0, 10)


class TestCandlesBaseAdapterResetWithDataFrame:
    """Test reset_with_dataframe for MarketDataProvider compatibility."""

    def test_reset_clears_and_repopulates(self):
        from candles_feed.hb_compat.adapter import CandlesBaseAdapter
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT", max_records=10
        )
        adapter._feed.add_candle(_make_candle(500))
        assert len(adapter._feed.get_candles()) == 1

        df = pd.DataFrame([
            [1000, 100.0, 101.0, 99.0, 100.5, 1000.0, 100000.0, 50, 500.0, 50000.0],
            [1060, 101.0, 102.0, 100.0, 101.5, 1100.0, 110000.0, 55, 550.0, 55000.0],
        ], columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "quote_asset_volume", "n_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume",
        ])
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
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT", max_records=10
        )
        df = pd.DataFrame([
            [1000, 100.0, 101.0, 99.0, 100.5, 1000.0],
        ], columns=["timestamp", "open", "high", "low", "close", "volume"])
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
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT", max_records=10
        )
        df = pd.DataFrame([
            [1000, 100.0, 101.0, 99.0, 100.5, 1000.0, float("nan"), float("nan"), float("nan"), float("nan")],
        ], columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "quote_asset_volume", "n_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume",
        ])
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
        adapter = CandlesBaseAdapter(
            exchange="binance", trading_pair="BTC-USDT"
        )
        adapter._feed.add_candle(_make_candle(500))

        adapter.reset_with_dataframe(pd.DataFrame())
        assert len(adapter._feed.get_candles()) == 0
