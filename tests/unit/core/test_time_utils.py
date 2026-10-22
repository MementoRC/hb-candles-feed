"""time_utils helpers: legacy behaviour without ``interval``, calendar-aware with it."""

from datetime import UTC, datetime

from candles_feed.utils.time_utils import calculate_start_end_times, round_timestamp_to_interval


def _ts(year: int, month: int, day: int = 1) -> int:
    return int(datetime(year, month, day, tzinfo=UTC).timestamp())


def test_round_without_interval_is_modulo():
    assert round_timestamp_to_interval(1_700_000_123, 60) == 1_700_000_123 - 23


def test_start_end_without_interval_is_fixed_step():
    start, end = calculate_start_end_times(1_700_000_123, 3600, 5)
    assert end == 1_700_000_123 - 1_700_000_123 % 3600
    assert start == end - 4 * 3600


def test_round_monthly_and_weekly():
    assert round_timestamp_to_interval(_ts(2024, 2, 20) + 5, 2592000, "1M") == _ts(2024, 2)
    assert round_timestamp_to_interval(_ts(2023, 5, 4) + 5, 604800, "1w") == _ts(2023, 5, 1)


def test_start_end_monthly_spans_calendar_months():
    start, end = calculate_start_end_times(_ts(2024, 3, 15), 2592000, 3, "1M")
    assert (start, end) == (_ts(2024, 1), _ts(2024, 3))
