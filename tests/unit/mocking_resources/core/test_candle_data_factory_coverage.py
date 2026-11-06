"""
Behavioural coverage tests for CandleDataFactory.
"""

import random

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core import candle_data_factory as cdf_module
from candles_feed.mocking_resources.core.candle_data_factory import CandleDataFactory


@pytest.fixture(autouse=True)
def seeded_random():
    random.seed(1234)


def make_candle(ts: int, open_: float, close: float) -> CandleData:
    return CandleData(
        timestamp_raw=ts,
        open=open_,
        high=max(open_, close) + 1,
        low=min(open_, close) - 1,
        close=close,
        volume=10.0,
        quote_asset_volume=10.0 * open_,
        n_trades=100,
        taker_buy_base_volume=5.0,
        taker_buy_quote_volume=5.0 * open_,
    )


class TestCreateRandom:
    def test_ohlc_invariants_and_ranges(self):
        for _ in range(50):
            c = CandleDataFactory.create_random(timestamp=1_700_000_000)
            assert c.timestamp == 1_700_000_000
            assert c.open == 50000.0
            assert c.high >= max(c.open, c.close)
            assert c.low <= min(c.open, c.close)
            assert 10.0 <= c.volume <= 30.0
            assert 0.4 * c.volume <= c.taker_buy_base_volume <= 0.6 * c.volume
            assert c.n_trades >= 50 + int(c.volume * 5)

    def test_previous_candle_close_becomes_open(self):
        prev = make_candle(1_700_000_000, 100.0, 123.0)
        c = CandleDataFactory.create_random(timestamp=1_700_000_060, previous_candle=prev)
        assert c.open == 123.0

    def test_close_is_clamped_to_max_deviation(self):
        # volatility large enough that the unclamped close would leave the band
        for _ in range(30):
            c = CandleDataFactory.create_random(
                timestamp=1_700_000_000,
                base_price=100.0,
                volatility=0.5,
                max_deviation=0.01,
                initial_price=100.0,
            )
            assert 99.0 <= c.close <= 101.0

    def test_initial_price_defaults_to_base_price(self):
        for _ in range(30):
            c = CandleDataFactory.create_random(
                timestamp=1_700_000_000, base_price=200.0, volatility=0.5, max_deviation=0.02
            )
            assert 196.0 <= c.close <= 204.0


class TestTrendingSeries:
    def test_count_spacing_and_start_price_band(self):
        series = CandleDataFactory.create_trending_series(
            start_timestamp=1_700_000_000,
            count=25,
            interval_seconds=300,
            start_price=1000.0,
            trend=0.01,
            volatility=0.02,
            max_deviation=0.05,
        )
        assert len(series) == 25
        assert [c.timestamp for c in series] == [1_700_000_000 + i * 300 for i in range(25)]
        assert all(950.0 <= c.close <= 1050.0 for c in series)

    def test_candles_chain_open_to_previous_close(self):
        series = CandleDataFactory.create_trending_series(1_700_000_000, 10, 60)
        for prev, nxt in zip(series, series[1:], strict=False):
            assert nxt.open == prev.close

    def test_zero_count_is_empty(self):
        assert CandleDataFactory.create_trending_series(1_700_000_000, 0, 60) == []


class TestPriceEvent:
    @pytest.fixture
    def candles(self):
        return CandleDataFactory.create_trending_series(1_700_000_000, 10, 60, start_price=100.0)

    def test_empty_input_returned_unchanged(self):
        empty: list[CandleData] = []
        assert CandleDataFactory.create_price_event(empty, 0) is empty

    def test_out_of_range_index_returned_unchanged(self, candles):
        assert CandleDataFactory.create_price_event(candles, len(candles)) is candles

    def test_spike_raises_close_and_boosts_volume(self, candles, monkeypatch):
        monkeypatch.setattr(cdf_module.random, "random", lambda: 0.9)
        original = candles[0]
        result = CandleDataFactory.create_price_event(candles, 0, event_magnitude=0.02)
        event = result[0]
        assert event.close == pytest.approx(original.open * 1.02)
        assert event.high >= event.close
        assert event.volume == pytest.approx(original.volume * (1.5 + 0.9 * 1.5))
        assert result is not candles
        assert candles[0] is original

    def test_drop_lowers_close_and_low(self, candles, monkeypatch):
        monkeypatch.setattr(cdf_module.random, "random", lambda: 0.1)
        result = CandleDataFactory.create_price_event(candles, 0, event_magnitude=0.02)
        assert result[0].close == pytest.approx(candles[0].open * 0.98)
        assert result[0].low <= result[0].close

    def test_magnitude_capped_at_half_of_max_deviation(self, candles, monkeypatch):
        monkeypatch.setattr(cdf_module.random, "random", lambda: 0.9)
        result = CandleDataFactory.create_price_event(
            candles, 0, event_magnitude=0.5, max_deviation=0.04
        )
        assert result[0].close == pytest.approx(candles[0].open * 1.02)

    def test_close_clamped_against_first_candle_open(self, monkeypatch):
        monkeypatch.setattr(cdf_module.random, "random", lambda: 0.9)
        series = [
            make_candle(1_700_000_000, 100.0, 104.0),
            make_candle(1_700_000_060, 104.0, 104.0),
        ]
        result = CandleDataFactory.create_price_event(
            series, 1, event_magnitude=0.05, max_deviation=0.05
        )
        assert result[1].close == pytest.approx(105.0)

    def test_subsequent_candles_rebuilt_from_event_close(self, candles, monkeypatch):
        monkeypatch.setattr(cdf_module.random, "random", lambda: 0.9)
        result = CandleDataFactory.create_price_event(candles, 3)
        assert result[4].open == result[3].close
        assert [c.timestamp for c in result] == [c.timestamp for c in candles]
        assert result[:3] == candles[:3]

    def test_last_index_has_nothing_to_rebuild(self, candles):
        result = CandleDataFactory.create_price_event(candles, len(candles) - 1)
        assert result[:-1] == candles[:-1]
        assert result[-1] != candles[-1]


class TestMarketSimulation:
    def test_length_and_timestamps(self):
        series = CandleDataFactory.create_market_simulation(1_700_000_000, 30, 60, 500.0)
        assert [c.timestamp for c in series] == [1_700_000_000 + i * 60 for i in range(30)]

    def test_events_placed_after_buffer(self, monkeypatch):
        calls = []
        real = CandleDataFactory.create_price_event

        def spy(**kwargs):
            calls.append(kwargs["event_index"])
            return real(**kwargs)

        monkeypatch.setattr(CandleDataFactory, "create_price_event", staticmethod(spy))
        monkeypatch.setattr(cdf_module.random, "randint", lambda lo, hi: lo)
        CandleDataFactory.create_market_simulation(1_700_000_000, 100, 60)
        assert calls == [10]
