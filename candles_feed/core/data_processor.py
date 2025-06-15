"""
Data processing utilities for the Candle Feed framework.
"""

import bisect
import logging
from collections import deque
from collections.abc import Sequence
from typing import Deque

from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import Logger


class DataProcessor:
    """Handles data processing, validation, and sanitization.

    This class provides methods for processing and validating candle data,
    ensuring that the data is consistent and reliable. Optimized for performance
    with binary search and efficient data structures.
    """

    def __init__(self, logger: Logger | None = None):
        """Initialize the DataProcessor.

        :param logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

        # Cache for timestamp lookups to avoid repeated conversions
        self._timestamp_cache: dict[int, int] = {}

    def sanitize_candles(
        self, candles: Sequence[CandleData], interval_in_seconds: int
    ) -> list[CandleData]:
        """Find and return the longest valid sequence of candles.

        This is important to handle exchange inconsistencies where:
        1. Candles may have unexpected gaps
        2. Intervals might not be uniform
        3. Candles might be out of order

        Optimized for performance with early exit conditions and vectorized operations.

        :param candles: Sequence of candle data
        :param interval_in_seconds: Expected interval between candles in seconds
        :return: List of validated, chronological candles with uniform intervals
        """
        if not candles:
            return []

        # Check if already sorted to avoid unnecessary sorting
        is_sorted = True
        if len(candles) > 1:
            for i in range(len(candles) - 1):
                if candles[i].timestamp > candles[i + 1].timestamp:
                    is_sorted = False
                    break

        # Sort only if necessary
        sorted_candles: list[CandleData] = (
            list(candles) if is_sorted else sorted(candles, key=lambda x: x.timestamp)
        )

        if len(sorted_candles) == 1:
            return [sorted_candles[0]]

        # Use vectorized approach for finding longest sequence
        timestamps = [c.timestamp for c in sorted_candles]
        differences = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]

        # Find longest continuous sequence with correct interval
        best_start = 0
        best_length = 1
        current_start = 0
        current_length = 1

        for i, diff in enumerate(differences):
            if diff == interval_in_seconds:
                current_length += 1
            else:
                # Check if current sequence is better
                if current_length > best_length:
                    best_start = current_start
                    best_length = current_length
                current_start = i + 1
                current_length = 1

        # Check the last sequence
        if current_length > best_length:
            best_start = current_start
            best_length = current_length

        # Return the best sequence found
        if best_length == 1 and len(differences) > 0:
            self.logger.warning("No valid candle sequences found. Returning most recent candle.")
            return [sorted_candles[-1]]

        result = sorted_candles[best_start : best_start + best_length]
        self.logger.debug(f"Found sequence of {len(result)} valid candles out of {len(candles)}")
        return result

    def validate_candle_intervals(
        self, candles: Sequence[CandleData], interval_in_seconds: int
    ) -> bool:
        """Validate that all candles have the correct interval.

        :param candles: Sequence of candle data
        :param interval_in_seconds: Expected interval between candles in seconds
        :return: True if all candles have the correct interval, False otherwise
        """
        if len(candles) <= 1:
            return True

        sorted_candles = sorted(candles, key=lambda x: x.timestamp)

        return all(
            sorted_candles[i + 1].timestamp - sorted_candles[i].timestamp == interval_in_seconds
            for i in range(len(sorted_candles) - 1)
        )

    def process_candle(self, candle: CandleData, candles_store: deque[CandleData]) -> None:
        """Process a single candle and add it to the store.

        Optimized version using binary search for efficient insertion and O(1)
        checks for common cases (append/prepend).

        :param candle: Candle to process
        :param candles_store: Store to add the candle to
        """
        if not candles_store:
            candles_store.append(candle)
            return

        candle_timestamp = candle.timestamp

        # Fast path: check if it's a simple append (most common case)
        if candle_timestamp >= candles_store[-1].timestamp:
            if candle_timestamp == candles_store[-1].timestamp:
                # Update existing candle at the end
                candles_store[-1] = candle
            else:
                # Simple append
                candles_store.append(candle)
            return

        # Fast path: check if it's a simple prepend
        if candle_timestamp <= candles_store[0].timestamp:
            if candle_timestamp == candles_store[0].timestamp:
                # Update existing candle at the beginning
                candles_store[0] = candle
            else:
                # Simple prepend
                candles_store.appendleft(candle)
            return

        # Slower path: need to insert in middle
        # Convert to list for binary search
        timestamps = [c.timestamp for c in candles_store]

        # Use binary search to find insertion point
        insert_pos = bisect.bisect_left(timestamps, candle_timestamp)

        # Check if we're updating an existing candle
        if insert_pos < len(timestamps) and timestamps[insert_pos] == candle_timestamp:
            # Update existing candle
            candles_store[insert_pos] = candle
        else:
            # Need to insert in middle - convert to list, insert, then reconstruct deque
            temp_list = list(candles_store)
            temp_list.insert(insert_pos, candle)

            # Reconstruct deque efficiently
            candles_store.clear()
            candles_store.extend(temp_list)

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for performance monitoring.

        :return: Dictionary with cache statistics
        """
        return {
            "timestamp_cache_size": len(self._timestamp_cache),
            "timestamp_cache_max_size": 1000,  # Arbitrary limit for monitoring
        }

    def clear_cache(self) -> None:
        """Clear internal caches to free memory."""
        self._timestamp_cache.clear()
