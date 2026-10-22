"""
Calendar-aware interval helpers for the Candle Feed framework.

Weekly (``1w``) and monthly (``1M``) candles follow the calendar (Monday start,
variable month length) rather than a fixed number of seconds. All arithmetic is UTC.
"""

from datetime import UTC, datetime

CALENDAR_INTERVALS = frozenset({"1w", "1M"})

_DAY = 86400


def is_calendar_interval(interval: str | None) -> bool:
    """Return True if the interval follows the calendar rather than a fixed length.

    :param interval: Interval string such as "1m" or "1M"
    :return: True for "1w" and "1M"
    """
    return interval in CALENDAR_INTERVALS


def _month_start(year: int, month: int) -> int:
    return int(datetime(year, month, 1, tzinfo=UTC).timestamp())


def _shift_months(ts: int, n: int) -> int:
    dt = datetime.fromtimestamp(ts, UTC)
    index = dt.year * 12 + (dt.month - 1) + n
    return _month_start(index // 12, index % 12 + 1)


def floor_timestamp(ts: int, interval: str | None, interval_seconds: int) -> int:
    """Floor a timestamp to the start of its candle bucket.

    :param ts: Timestamp in seconds
    :param interval: Interval string such as "1m", "1w" or "1M"
    :param interval_seconds: Nominal interval length in seconds
    :return: Bucket start (1st of month / Monday 00:00 UTC for calendar intervals)
    """
    if interval == "1M":
        return _shift_months(ts, 0)
    if interval == "1w":
        day_start = ts - ts % _DAY
        weekday = datetime.fromtimestamp(day_start, UTC).weekday()
        return day_start - weekday * _DAY
    return ts - ts % interval_seconds


def next_boundary(ts: int, interval: str | None, interval_seconds: int) -> int:
    """Return the start of the bucket following the one containing the timestamp.

    :param ts: Timestamp in seconds
    :param interval: Interval string such as "1m", "1w" or "1M"
    :param interval_seconds: Nominal interval length in seconds
    :return: Start of the next bucket
    """
    return shift_boundaries(ts, interval, interval_seconds, 1)


def shift_boundaries(ts: int, interval: str | None, interval_seconds: int, n: int) -> int:
    """Floor a timestamp then step n buckets (negative for backwards).

    :param ts: Timestamp in seconds
    :param interval: Interval string such as "1m", "1w" or "1M"
    :param interval_seconds: Nominal interval length in seconds
    :param n: Number of buckets to move, negative for earlier
    :return: Start of the bucket n steps from the one containing the timestamp
    """
    if interval == "1M":
        return _shift_months(ts, n)
    start = floor_timestamp(ts, interval, interval_seconds)
    if interval == "1w":
        return start + n * 7 * _DAY
    return start + n * interval_seconds
