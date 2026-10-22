"""Calendar-aware (1w / 1M) behaviour of DataProcessor."""

from datetime import UTC, datetime

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.core.data_processor import DataProcessor

MONTH = 2592000
WEEK = 604800


def _ts(year: int, month: int, day: int = 1) -> int:
    return int(datetime(year, month, day, tzinfo=UTC).timestamp())


def _candle(t: int) -> CandleData:
    return CandleData(t, 1.0, 2.0, 0.5, 1.5, 10.0)


def _month_starts(n: int = 13, year: int = 2023, month: int = 1) -> list[int]:
    out = []
    for i in range(n):
        m = month - 1 + i
        out.append(_ts(year + m // 12, m % 12 + 1))
    return out


def test_sanitize_keeps_all_real_months_with_interval():
    stamps = _month_starts(13)
    result = DataProcessor().sanitize_candles([_candle(t) for t in stamps], MONTH, "1M")
    assert [c.timestamp for c in result] == stamps


def test_sanitize_without_interval_collapses_monthly_series():
    """Legacy behaviour: no interval means fixed 2592000s diffs, so real months collapse."""
    stamps = _month_starts(13)
    result = DataProcessor().sanitize_candles([_candle(t) for t in stamps], MONTH)
    # Only 30-day months (Apr->May, Jun->Jul, ...) match the fixed diff; longest run is 2.
    assert len(result) == 2
    assert len(result) < len(stamps)


def test_sanitize_splits_on_missing_month():
    stamps = _month_starts(13)
    del stamps[4]  # drop May 2023 -> runs of 4 and 8
    result = DataProcessor().sanitize_candles([_candle(t) for t in stamps], MONTH, "1M")
    assert [c.timestamp for c in result] == stamps[4:]


def test_validate_true_for_real_months_with_interval():
    candles = [_candle(t) for t in _month_starts(13)]
    dp = DataProcessor()
    assert dp.validate_candle_intervals(candles, MONTH, "1M") is True
    assert dp.validate_candle_intervals(candles, MONTH) is False


def test_validate_false_for_missing_month():
    stamps = _month_starts(6)
    del stamps[2]
    assert (
        DataProcessor().validate_candle_intervals([_candle(t) for t in stamps], MONTH, "1M")
        is False
    )


def test_validate_false_and_sanitize_drops_mid_month_first_candle():
    stamps = [_ts(2023, 1, 15), *_month_starts(6)[1:]]
    candles = [_candle(t) for t in stamps]
    dp = DataProcessor()
    assert dp.validate_candle_intervals(candles, MONTH, "1M") is False
    assert [c.timestamp for c in dp.sanitize_candles(candles, MONTH, "1M")] == stamps[1:]


@pytest.mark.parametrize("day", [1, 4, 7])  # Monday, Thursday, Sunday
def test_weekly_any_weekday_uses_fixed_step(day):
    start = _ts(2023, 5, day)
    stamps = [start + i * WEEK for i in range(10)]
    dp = DataProcessor()
    candles = [_candle(t) for t in stamps]
    assert [c.timestamp for c in dp.sanitize_candles(candles, WEEK, "1w")] == stamps
    assert dp.validate_candle_intervals(candles, WEEK, "1w") is True


def test_fixed_interval_unchanged_with_interval_arg():
    stamps = [1_700_000_000 + i * 60 for i in range(5)]
    result = DataProcessor().sanitize_candles([_candle(t) for t in stamps], 60, "1m")
    assert [c.timestamp for c in result] == stamps
