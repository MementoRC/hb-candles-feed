"""
Time-related utility functions for the Candle Feed framework.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Tuple


def round_timestamp_to_interval(timestamp: int, interval_seconds: int) -> int:
    """Round timestamp to the nearest interval.

    Args:
        timestamp: Timestamp in seconds
        interval_seconds: Interval in seconds

    Returns:
        Rounded timestamp
    """
    return timestamp - (timestamp % interval_seconds)


def calculate_start_end_times(
    end_time: int, interval_seconds: int, num_candles: int
) -> Tuple[int, int]:
    """Calculate start and end times for fetching candles.

    Args:
        end_time: End time in seconds
        interval_seconds: Interval in seconds
        num_candles: Number of candles to fetch

    Returns:
        Tuple of (start_time, end_time) in seconds
    """
    # Round end time to the nearest interval
    rounded_end = round_timestamp_to_interval(end_time, interval_seconds)

    # Calculate start time
    start_time = rounded_end - ((num_candles - 1) * interval_seconds)

    return start_time, rounded_end


def current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds.

    Returns:
        Current timestamp in milliseconds
    """
    return int(time.time() * 1000)


def current_timestamp_s() -> int:
    """Get current timestamp in seconds.

    Returns:
        Current timestamp in seconds
    """
    return int(time.time())


def timestamp_to_datetime(timestamp: int) -> datetime:
    """Convert timestamp to datetime.

    Args:
        timestamp: Timestamp in seconds

    Returns:
        Datetime object
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to timestamp.

    Args:
        dt: Datetime object

    Returns:
        Timestamp in seconds
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())
