"""
Time-related utility functions for the Candle Feed framework.
"""

import time
from datetime import UTC, datetime, timezone

from candles_feed.core.intervals import floor_timestamp, shift_boundaries


def round_timestamp_to_interval(
    timestamp: int, interval_seconds: int, interval: str | None = None
) -> int:
    """Round timestamp down to the start of its interval bucket.

    :param timestamp: Timestamp in seconds
    :param interval_seconds: Interval in seconds
    :param interval: Optional interval string; "1w" and "1M" use calendar boundaries
    :returns: Rounded timestamp
    """
    return floor_timestamp(timestamp, interval, interval_seconds)


def calculate_start_end_times(
    end_time: int, interval_seconds: int, num_candles: int, interval: str | None = None
) -> tuple[int, int]:
    """Calculate start and end times for fetching candles.

    :param end_time: End time in seconds
    :param interval_seconds: Interval in seconds
    :param num_candles: Number of candles to fetch
    :param interval: Optional interval string; "1w" and "1M" use calendar boundaries
    :returns: Tuple of (start_time, end_time) in seconds
    """
    # Round end time to the nearest interval
    rounded_end = round_timestamp_to_interval(end_time, interval_seconds, interval)

    # Calculate start time
    start_time = shift_boundaries(rounded_end, interval, interval_seconds, -(num_candles - 1))

    return start_time, rounded_end


def current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds.

    :returns: Current timestamp in milliseconds
    """
    return int(time.time() * 1000)


def current_timestamp_s() -> int:
    """Get current timestamp in seconds.

    Returns:
        Current timestamp in seconds
    """
    return int(time.time())


def ensure_timestamp_in_seconds(timestamp: float | int | str) -> float:
    """Ensure the given timestamp is in seconds.

    Mirrors hummingbot's ``CandlesBase.ensure_timestamp_in_seconds``.

    :param timestamp: Timestamp in seconds, milliseconds, microseconds or nanoseconds
    :returns: Timestamp in seconds
    :raises ValueError: If the timestamp is not in a recognized format
    """
    timestamp_int = int(float(timestamp))
    if timestamp_int >= 1e18:  # Nanoseconds
        return timestamp_int / 1e9
    if timestamp_int >= 1e15:  # Microseconds
        return timestamp_int / 1e6
    if timestamp_int >= 1e12:  # Milliseconds
        return timestamp_int / 1e3
    if timestamp_int >= 1e9:  # Seconds
        return timestamp_int
    raise ValueError(
        "Timestamp is not in a recognized format. "
        "Must be in seconds, milliseconds, microseconds or nanoseconds."
    )


def timestamp_to_datetime(timestamp: int) -> datetime:
    """ "Convert timestamp to datetime.

    :param timestamp: Timestamp in seconds
    :returns: Datetime object
    """
    return datetime.fromtimestamp(timestamp, tz=UTC)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to timestamp.

    :param dt: Datetime object
    :returns: Timestamp in seconds
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())
