#!/usr/bin/env python3
"""
Task 9 Validation: DataFrame and CandleData Compatibility

This script validates that DataFrame column names/types, CandleData.to_array() output,
timestamp rounding, and check_candles_sorted_and_equidistant logic match the original
Hummingbot implementation.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.utils.time_utils import round_timestamp_to_interval

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_candle_data_to_array():
    """Test 1: Validate CandleData.to_array() format and precision."""
    logger.info("=== Test 1: CandleData.to_array() Format Validation ===")

    # Create test candle with known values
    test_candle = CandleData(
        timestamp_raw=1609459200,  # 2021-01-01 00:00:00 UTC
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=100.0,
        quote_asset_volume=5000000.0,
        n_trades=1000,
        taker_buy_base_volume=60.0,
        taker_buy_quote_volume=3000000.0,
    )

    # Get array representation
    array_output = test_candle.to_array()

    # Expected format based on original Hummingbot specification
    expected_format = [
        float(1609459200),  # timestamp as float
        50000.0,  # open
        51000.0,  # high
        49000.0,  # low
        50500.0,  # close
        100.0,  # volume
        5000000.0,  # quote_asset_volume
        1000,  # n_trades (converted to float in array)
        60.0,  # taker_buy_base_volume
        3000000.0,  # taker_buy_quote_volume
    ]

    # Validate array length
    assert len(array_output) == 10, f"Expected 10 elements, got {len(array_output)}"

    # Validate each element
    for i, (actual, expected) in enumerate(zip(array_output, expected_format)):
        assert actual == expected, f"Mismatch at index {i}: {actual} != {expected}"
        assert isinstance(
            actual, (int, float)
        ), f"Element {i} should be numeric, got {type(actual)}"

    # Test timestamp precision with different input formats
    timestamp_tests = [
        (1609459200, 1609459200.0),  # int seconds
        (1609459200000, 1609459200.0),  # milliseconds
        (1609459200000000, 1609459200.0),  # microseconds
        ("1609459200", 1609459200.0),  # string
        ("2021-01-01T00:00:00Z", 1609459200.0),  # ISO format
        (datetime(2021, 1, 1, tzinfo=timezone.utc), 1609459200.0),  # datetime
    ]

    for input_ts, expected_ts in timestamp_tests:
        candle = CandleData(
            timestamp_raw=input_ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=1000.0
        )
        array_result = candle.to_array()
        assert (
            array_result[0] == expected_ts
        ), f"Timestamp conversion failed for {input_ts}: {array_result[0]} != {expected_ts}"

    logger.info("✅ CandleData.to_array() format validation passed")


def validate_dataframe_structure():
    """Test 2: Validate DataFrame column names, types, and structure."""
    logger.info("\n=== Test 2: DataFrame Structure Validation ===")

    # Create sample candles
    sample_candles = [
        CandleData(
            timestamp_raw=1609459200 + i * 60,
            open=50000.0 + i * 100,
            high=51000.0 + i * 100,
            low=49000.0 + i * 100,
            close=50500.0 + i * 100,
            volume=100.0,
            quote_asset_volume=5000000.0,
            n_trades=1000,
            taker_buy_base_volume=60.0,
            taker_buy_quote_volume=3000000.0,
        )
        for i in range(5)
    ]

    # Create DataFrame using CandlesFeed method

    mock_adapter = MagicMock()
    mock_adapter.get_supported_intervals.return_value = {"1m": 60}

    with patch(
        "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
        return_value=mock_adapter,
    ), patch(
        "candles_feed.core.network_client.NetworkClient",
        return_value=MagicMock(),
    ):
        feed = CandlesFeed(
            exchange="test_exchange",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100,
        )

        # Add candles
        for candle in sample_candles:
            feed.add_candle(candle)

        # Get DataFrame
        df = feed.get_candles_df()

        # Expected column names (must match original Hummingbot specification)
        expected_columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_asset_volume",
            "n_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
        ]

        # Validate column names
        assert (
            list(df.columns) == expected_columns
        ), f"Column mismatch: {list(df.columns)} != {expected_columns}"

        # Validate data types
        expected_types = {
            "timestamp": ("int64", "int32", "float64"),  # Allow multiple timestamp formats
            "open": ("float64",),
            "high": ("float64",),
            "low": ("float64",),
            "close": ("float64",),
            "volume": ("float64",),
            "quote_asset_volume": ("float64",),
            "n_trades": ("int64", "int32", "float64"),  # Allow int or float
            "taker_buy_base_volume": ("float64",),
            "taker_buy_quote_volume": ("float64",),
        }

        for col, allowed_types in expected_types.items():
            actual_type = str(df[col].dtype)
            assert (
                actual_type in allowed_types
            ), f"Type mismatch for {col}: {actual_type} not in {allowed_types}"

        # Validate DataFrame content
        assert len(df) == 5, f"Expected 5 rows, got {len(df)}"

        # Validate specific values
        first_row = df.iloc[0]
        assert first_row["timestamp"] == 1609459200
        assert first_row["open"] == 50000.0
        assert first_row["high"] == 51000.0
        assert first_row["volume"] == 100.0

        # Test DataFrame conversion to array format (for compatibility)
        array_data = df.values.tolist()
        assert len(array_data) == 5, "Array conversion should preserve row count"
        assert len(array_data[0]) == 10, "Array conversion should preserve column count"

        logger.info("✅ DataFrame structure validation passed")


def validate_timestamp_rounding():
    """Test 3: Validate timestamp rounding behavior."""
    logger.info("\n=== Test 3: Timestamp Rounding Validation ===")

    # Test cases: (input_timestamp, interval_seconds, expected_output)
    test_cases = [
        # 1-minute interval tests
        (1609459217, 60, 1609459200),  # Round down within interval
        (1609459200, 60, 1609459200),  # Exact boundary
        (1609459259, 60, 1609459200),  # Round down near end
        (1609459260, 60, 1609459260),  # Next boundary
        # 5-minute interval tests
        (1609459200, 300, 1609459200),  # Exact 5m boundary
        (1609459217, 300, 1609459200),  # Round down within 5m
        (1609459499, 300, 1609459200),  # Round down near end of 5m
        (1609459500, 300, 1609459500),  # Next 5m boundary
        # 1-hour interval tests
        (1609459200, 3600, 1609459200),  # Exact hour boundary
        (1609459217, 3600, 1609459200),  # Round down within hour
        (1609462799, 3600, 1609459200),  # Round down near end of hour
        (1609462800, 3600, 1609462800),  # Next hour boundary
        # Edge cases
        (0, 60, 0),  # Unix epoch
        (1609459200, 1, 1609459200),  # 1-second interval
    ]

    for input_ts, interval_sec, expected in test_cases:
        # Test utility function
        result_util = round_timestamp_to_interval(input_ts, interval_sec)
        assert (
            result_util == expected
        ), f"Utility function failed: round_timestamp_to_interval({input_ts}, {interval_sec}) = {result_util}, expected {expected}"

        # Test CandlesFeed method (requires mock setup)
        mock_adapter = MagicMock()
        interval_map = {60: "1m", 300: "5m", 3600: "1h", 1: "1s"}
        interval_str = interval_map.get(interval_sec, "1m")
        mock_adapter.get_supported_intervals.return_value = {interval_str: interval_sec}

        with patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=mock_adapter,
        ), patch(
            "candles_feed.core.network_client.NetworkClient",
            return_value=MagicMock(),
        ):
            feed = CandlesFeed(
                exchange="test_exchange",
                trading_pair="BTC-USDT",
                interval=interval_str,
                max_records=10,
            )

            result_feed = feed._round_timestamp_to_interval_multiple(input_ts)
            assert (
                result_feed == expected
            ), f"CandlesFeed method failed: _round_timestamp_to_interval_multiple({input_ts}) = {result_feed}, expected {expected}"

    logger.info("✅ Timestamp rounding validation passed")


def validate_check_candles_sorted_and_equidistant():
    """Test 4: Validate check_candles_sorted_and_equidistant logic."""
    logger.info("\n=== Test 4: check_candles_sorted_and_equidistant Validation ===")

    mock_adapter = MagicMock()
    mock_adapter.get_supported_intervals.return_value = {"1m": 60}

    with patch(
        "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
        return_value=mock_adapter,
    ), patch(
        "candles_feed.core.network_client.NetworkClient",
        return_value=MagicMock(),
    ):
        feed = CandlesFeed(
            exchange="test_exchange",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=10,
        )

        # Test 1: Empty candles (should return True)
        assert feed.check_candles_sorted_and_equidistant(), "Empty candles should return True"

        # Test 2: Single candle (should return True)
        feed.add_candle(
            CandleData(
                timestamp_raw=1609459200,
                open=50000.0,
                high=51000.0,
                low=49000.0,
                close=50500.0,
                volume=100.0,
            )
        )
        assert feed.check_candles_sorted_and_equidistant(), "Single candle should return True"

        # Test 3: Properly sorted and equidistant candles
        for i in range(1, 5):
            feed.add_candle(
                CandleData(
                    timestamp_raw=1609459200 + i * 60,  # 60-second intervals
                    open=50000.0,
                    high=51000.0,
                    low=49000.0,
                    close=50500.0,
                    volume=100.0,
                )
            )

        assert (
            feed.check_candles_sorted_and_equidistant()
        ), "Sorted equidistant candles should return True"

        # Test 4: External data validation (using array format)
        external_data = [
            [1609459200, 50000.0, 51000.0, 49000.0, 50500.0, 100.0, 0.0, 0, 0.0, 0.0],
            [1609459260, 50100.0, 51100.0, 49100.0, 50600.0, 100.0, 0.0, 0, 0.0, 0.0],
            [1609459320, 50200.0, 51200.0, 49200.0, 50700.0, 100.0, 0.0, 0, 0.0, 0.0],
        ]

        assert feed.check_candles_sorted_and_equidistant(
            external_data
        ), "External sorted data should return True"

        # Test 5: Unsorted data (should return False)
        unsorted_data = [
            [
                1609459260,
                50100.0,
                51100.0,
                49100.0,
                50600.0,
                100.0,
                0.0,
                0,
                0.0,
                0.0,
            ],  # Later timestamp first
            [
                1609459200,
                50000.0,
                51000.0,
                49000.0,
                50500.0,
                100.0,
                0.0,
                0,
                0.0,
                0.0,
            ],  # Earlier timestamp second
        ]

        assert not feed.check_candles_sorted_and_equidistant(
            unsorted_data
        ), "Unsorted data should return False"

        # Test 6: Non-equidistant data (should return False)
        non_equidistant_data = [
            [1609459200, 50000.0, 51000.0, 49000.0, 50500.0, 100.0, 0.0, 0, 0.0, 0.0],
            [
                1609459230,
                50100.0,
                51100.0,
                49100.0,
                50600.0,
                100.0,
                0.0,
                0,
                0.0,
                0.0,
            ],  # 30-second gap instead of 60
            [
                1609459320,
                50200.0,
                51200.0,
                49200.0,
                50700.0,
                100.0,
                0.0,
                0,
                0.0,
                0.0,
            ],  # 90-second gap
        ]

        assert not feed.check_candles_sorted_and_equidistant(
            non_equidistant_data
        ), "Non-equidistant data should return False"

        # Test 7: Large dataset performance test
        start_time = time.time()
        large_dataset = [
            [1609459200 + i * 60, 50000.0, 51000.0, 49000.0, 50500.0, 100.0, 0.0, 0, 0.0, 0.0]
            for i in range(1000)  # 1000 candles
        ]
        result = feed.check_candles_sorted_and_equidistant(large_dataset)
        elapsed = time.time() - start_time

        assert result, "Large sorted dataset should return True"
        assert elapsed < 1.0, f"Large dataset validation should be fast, took {elapsed:.3f}s"

        logger.info("✅ check_candles_sorted_and_equidistant validation passed")


def validate_backward_compatibility():
    """Test 5: Validate backward compatibility features."""
    logger.info("\n=== Test 5: Backward Compatibility Validation ===")

    # Test array conversion roundtrip
    original_data = [
        1609459200.0,
        50000.0,
        51000.0,
        49000.0,
        50500.0,
        100.0,
        5000000.0,
        1000.0,
        60.0,
        3000000.0,
    ]

    # Convert array to CandleData and back
    candle = CandleData.from_array(original_data)
    converted_back = candle.to_array()

    # Validate roundtrip conversion
    for i, (original, converted) in enumerate(zip(original_data, converted_back)):
        if i == 7:  # n_trades gets converted to int then back to float
            assert int(original) == int(
                converted
            ), f"n_trades conversion mismatch at index {i}: {original} != {converted}"
        else:
            assert (
                original == converted
            ), f"Roundtrip conversion mismatch at index {i}: {original} != {converted}"

    # Test dictionary conversion with various key formats
    dict_tests = [
        # Standard format
        {
            "timestamp": 1609459200,
            "open": 50000.0,
            "high": 51000.0,
            "low": 49000.0,
            "close": 50500.0,
            "volume": 100.0,
            "quote_asset_volume": 5000000.0,
            "n_trades": 1000,
            "taker_buy_base_volume": 60.0,
            "taker_buy_quote_volume": 3000000.0,
        },
        # Short format (common in APIs)
        {"t": 1609459200, "o": 50000.0, "h": 51000.0, "l": 49000.0, "c": 50500.0, "v": 100.0},
        # Mixed format
        {
            "time": 1609459200,
            "open": 50000.0,
            "h": 51000.0,
            "l": 49000.0,
            "close": 50500.0,
            "volume": 100.0,
        },
    ]

    for i, dict_data in enumerate(dict_tests):
        candle = CandleData.from_dict(dict_data)
        assert candle.timestamp == 1609459200, f"Dict test {i}: timestamp mismatch"
        assert candle.open == 50000.0, f"Dict test {i}: open mismatch"
        assert candle.high == 51000.0, f"Dict test {i}: high mismatch"
        assert candle.low == 49000.0, f"Dict test {i}: low mismatch"
        assert candle.close == 50500.0, f"Dict test {i}: close mismatch"
        assert candle.volume == 100.0, f"Dict test {i}: volume mismatch"

    # Test timestamp format compatibility
    timestamp_formats = [
        1609459200,  # Unix seconds
        1609459200000,  # Unix milliseconds
        1609459200000000,  # Unix microseconds
        "1609459200",  # String seconds
        "2021-01-01T00:00:00Z",  # ISO format
        datetime(2021, 1, 1, tzinfo=timezone.utc),  # datetime object
    ]

    for ts_format in timestamp_formats:
        candle = CandleData(
            timestamp_raw=ts_format,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0,
        )
        assert (
            candle.timestamp == 1609459200
        ), f"Timestamp format {type(ts_format)} failed: {candle.timestamp}"

    logger.info("✅ Backward compatibility validation passed")


async def main():
    """Run all validation tests."""
    logger.info("🚀 Starting Task 9 Validation: DataFrame and CandleData Compatibility")

    try:
        validate_candle_data_to_array()
        validate_dataframe_structure()
        validate_timestamp_rounding()
        validate_check_candles_sorted_and_equidistant()
        validate_backward_compatibility()

        logger.info("\n🎉 All validation tests passed!")
        logger.info("✅ CandleData.to_array() format is compatible")
        logger.info("✅ DataFrame structure matches original specification")
        logger.info("✅ Timestamp rounding behavior is correct")
        logger.info("✅ check_candles_sorted_and_equidistant logic is robust")
        logger.info("✅ Backward compatibility features work correctly")
        logger.info("✅ Implementation is ready for production use")

        return True

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
