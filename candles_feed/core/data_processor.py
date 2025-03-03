"""
Data processing utilities for the Candle Feed framework.
"""

import logging
from collections import deque
from typing import Deque, List, Optional, Sequence

from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import Logger


class DataProcessor:
    """Handles data processing, validation, and sanitization.

    This class provides methods for processing and validating candle data,
    ensuring that the data is consistent and reliable.
    """

    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the DataProcessor.

        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def sanitize_candles(
        self, candles: Sequence[CandleData], interval_in_seconds: int
    ) -> List[CandleData]:
        """Find and return the longest valid sequence of candles.

        This is important to handle exchange inconsistencies where:
        1. Candles may have unexpected gaps
        2. Intervals might not be uniform
        3. Candles might be out of order

        Args:
            candles: Sequence of candle data
            interval_in_seconds: Expected interval between candles in seconds

        Returns:
            List of validated, chronological candles with uniform intervals
        """
        if not candles:
            return []

        # Sort candles by timestamp
        sorted_candles = sorted(candles, key=lambda x: x.timestamp)

        if len(sorted_candles) == 1:
            return [sorted_candles[0]]

        # Find longest continuous sequence with correct interval
        best_sequence = []
        current_sequence = []

        for i in range(len(sorted_candles) - 1):
            if not current_sequence:
                current_sequence = [i]

            # Check if the next candle is at the expected interval
            if sorted_candles[i + 1].timestamp - sorted_candles[i].timestamp == interval_in_seconds:
                current_sequence.append(i + 1)
            else:
                # Sequence broken, check if it's the longest so far
                if len(current_sequence) > len(best_sequence):
                    best_sequence = current_sequence
                current_sequence = []

        # Check the last sequence
        if len(current_sequence) > len(best_sequence):
            best_sequence = current_sequence

        # Return the best sequence found
        if not best_sequence:
            self.logger.warning("No valid candle sequences found. Returning most recent candle.")
            return [sorted_candles[-1]] if sorted_candles else []

        result = [sorted_candles[i] for i in best_sequence]
        self.logger.debug(f"Found sequence of {len(result)} valid candles out of {len(candles)}")
        return result

    def validate_candle_intervals(
        self, candles: Sequence[CandleData], interval_in_seconds: int
    ) -> bool:
        """Validate that all candles have the correct interval.

        Args:
            candles: Sequence of candle data
            interval_in_seconds: Expected interval between candles in seconds

        Returns:
            True if all candles have the correct interval, False otherwise
        """
        if len(candles) <= 1:
            return True

        sorted_candles = sorted(candles, key=lambda x: x.timestamp)

        for i in range(len(sorted_candles) - 1):
            if sorted_candles[i + 1].timestamp - sorted_candles[i].timestamp != interval_in_seconds:
                return False

        return True

    def process_candle(self, candle: CandleData, candles_store: Deque[CandleData]) -> None:
        """Process a single candle and add it to the store.

        Args:
            candle: Candle to process
            candles_store: Store to add the candle to
        """
        # Check if we already have this timestamp
        existing_indices = [
            i for i, c in enumerate(candles_store) if c.timestamp == candle.timestamp
        ]

        if existing_indices:
            # Update existing candle
            candles_store[existing_indices[0]] = candle
        else:
            # Add new candle if it belongs chronologically
            if not candles_store or candle.timestamp > candles_store[-1].timestamp:
                candles_store.append(candle)
            elif candle.timestamp < candles_store[0].timestamp:
                candles_store.appendleft(candle)
                # If deque is at capacity, the oldest item at the other end will be removed
            else:
                # Insert in the middle (rare case)
                temp_list = list(candles_store)
                for i in range(len(temp_list) - 1):
                    if temp_list[i].timestamp < candle.timestamp < temp_list[i + 1].timestamp:
                        temp_list.insert(i + 1, candle)
                        break

                # Clear and refill the deque
                candles_store.clear()
                for c in temp_list:
                    candles_store.append(c)
