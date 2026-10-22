"""Unit tests for calendar-aware interval helpers."""

from datetime import UTC, datetime

import pytest

from candles_feed.core.intervals import (
    CALENDAR_INTERVALS,
    ceil_timestamp,
    floor_timestamp,
    is_calendar_interval,
    is_valid_step,
    is_variable_length_interval,
    next_boundary,
    shift_boundaries,
)

MONTH = 2592000
WEEK = 604800


def ts(year, month, day, hour=0, minute=0, second=0) -> int:
    return int(datetime(year, month, day, hour, minute, second, tzinfo=UTC).timestamp())


def test_variable_length_only_month():
    assert is_variable_length_interval("1M")
    assert not is_variable_length_interval("1w")
    assert not is_variable_length_interval(None)


def test_ceil_timestamp():
    assert ceil_timestamp(ts(2024, 2, 1), "1M", MONTH) == ts(2024, 2, 1)
    assert ceil_timestamp(ts(2024, 2, 1, 0, 0, 1), "1M", MONTH) == ts(2024, 3, 1)
    assert ceil_timestamp(120, "1m", 60) == 120
    assert ceil_timestamp(121, "1m", 60) == 180


def test_is_valid_step():
    assert is_valid_step(ts(2024, 1, 1), ts(2024, 2, 1), "1M", MONTH)
    assert not is_valid_step(ts(2024, 1, 15), ts(2024, 2, 1), "1M", MONTH)
    assert not is_valid_step(ts(2024, 1, 1), ts(2024, 1, 1) + MONTH, "1M", MONTH)
    assert is_valid_step(ts(2023, 5, 4), ts(2023, 5, 4) + WEEK, "1w", WEEK)
    assert not is_valid_step(100, 170, "1m", 60)


def test_calendar_interval_membership():
    assert frozenset({"1w", "1M"}) == CALENDAR_INTERVALS
    assert is_calendar_interval("1M")
    assert is_calendar_interval("1w")
    assert not is_calendar_interval("1m")
    assert not is_calendar_interval("1d")
    assert not is_calendar_interval(None)


@pytest.mark.parametrize(
    ("year", "month", "days"),
    [(2023, 2, 28), (2024, 2, 29), (2023, 4, 30), (2023, 1, 31)],
)
def test_month_floor_and_next_for_month_lengths(year, month, days):
    start = ts(year, month, 1)
    mid = start + 5 * 86400 + 3723
    last_second = start + days * 86400 - 1

    assert floor_timestamp(start, "1M", MONTH) == start
    assert floor_timestamp(mid, "1M", MONTH) == start
    assert floor_timestamp(last_second, "1M", MONTH) == start
    assert next_boundary(mid, "1M", MONTH) - start == days * 86400
    assert next_boundary(start, "1M", MONTH) - start == days * 86400


def test_month_next_boundary_december_rolls_to_january():
    assert next_boundary(ts(2023, 12, 15), "1M", MONTH) == ts(2024, 1, 1)
    assert next_boundary(ts(2023, 12, 1), "1M", MONTH) == ts(2024, 1, 1)


@pytest.mark.parametrize("day", range(1, 8))
def test_week_floors_to_monday_for_every_weekday(day):
    # 2023-05-01 is a Monday; days 1..7 cover Mon..Sun
    t = ts(2023, 5, day, 13, 45, 12)
    floored = floor_timestamp(t, "1w", WEEK)
    assert datetime.fromtimestamp(floored, UTC).weekday() == 0
    assert floored == ts(2023, 5, 1)
    assert next_boundary(t, "1w", WEEK) == floored + WEEK


def test_week_floor_is_idempotent_on_monday():
    monday = ts(2024, 3, 4)
    assert floor_timestamp(monday, "1w", WEEK) == monday


@pytest.mark.parametrize(
    ("interval", "seconds"), [("1m", 60), ("1h", 3600), ("1d", 86400), (None, 300)]
)
def test_fixed_intervals_match_modulo(interval, seconds):
    t = 1_700_000_123
    assert floor_timestamp(t, interval, seconds) == t - t % seconds
    assert next_boundary(t, interval, seconds) == t - t % seconds + seconds
    assert shift_boundaries(t, interval, seconds, -3) == t - t % seconds - 3 * seconds
    assert shift_boundaries(t, interval, seconds, 2) == t - t % seconds + 2 * seconds


def test_shift_boundaries_months_back_and_forward():
    t = ts(2024, 3, 17, 10)
    assert shift_boundaries(t, "1M", MONTH, -1) == ts(2024, 2, 1)
    assert shift_boundaries(t, "1M", MONTH, -3) == ts(2023, 12, 1)
    assert shift_boundaries(t, "1M", MONTH, 0) == ts(2024, 3, 1)
    assert shift_boundaries(t, "1M", MONTH, 10) == ts(2025, 1, 1)


def test_shift_boundaries_minus_twelve_months_is_exactly_one_year():
    t = ts(2024, 7, 20, 8)
    assert shift_boundaries(t, "1M", MONTH, -12) == ts(2023, 7, 1)
    assert shift_boundaries(ts(2024, 1, 31), "1M", MONTH, -12) == ts(2023, 1, 1)


def test_shift_boundaries_weeks():
    t = ts(2023, 5, 4)  # Thursday
    assert shift_boundaries(t, "1w", WEEK, -2) == ts(2023, 4, 17)
    assert shift_boundaries(t, "1w", WEEK, 1) == ts(2023, 5, 8)
