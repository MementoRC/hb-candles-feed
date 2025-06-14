"""
Utils module for the Candles Feed framework.
"""

import time
from datetime import timedelta

from .profiling import BenchmarkSuite, PerformanceProfiler, default_profiler, profile_performance


def is_timestamp_recent(timestamp_s: int) -> bool:
    """
    Validates if a given timestamp (in seconds) is recent (within the last 24 hours).

    :param timestamp_s: The timestamp in seconds since the epoch.
    :return: True if the timestamp is within the last 24 hours, False otherwise.
    """
    now_s = int(time.time())
    twenty_four_hours_ago_s = now_s - int(timedelta(hours=24).total_seconds())
    return timestamp_s >= twenty_four_hours_ago_s


__all__ = [
    "BenchmarkSuite",
    "PerformanceProfiler",
    "profile_performance",
    "default_profiler",
    "is_timestamp_recent",
]
