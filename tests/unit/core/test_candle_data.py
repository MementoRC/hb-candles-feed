"""
Unit tests for the CandleData class.
"""

from datetime import datetime, timezone

import pytest

from candles_feed.core.candle_data import CandleData


class TestCandleData:
    """Test suite for the CandleData class."""

    def test_initialization_with_integer_timestamp(self):
        """Test initialization with timestamp as integer."""
        timestamp = 1622505600
        candle = CandleData(
            timestamp_raw=timestamp,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0,
        )

        assert candle.timestamp == timestamp
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        # Check default values
        assert candle.quote_asset_volume == 0.0
        assert candle.n_trades == 0
        assert candle.taker_buy_base_volume == 0.0
        assert candle.taker_buy_quote_volume == 0.0

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields specified."""
        timestamp = 1622505600
        candle = CandleData(
            timestamp_raw=timestamp,
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

        assert candle.timestamp == timestamp
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        assert candle.n_trades == 1000
        assert candle.taker_buy_base_volume == 60.0
        assert candle.taker_buy_quote_volume == 3000000.0

    @pytest.mark.parametrize(
        "timestamp_raw,expected_seconds",
        [
            (1622505600, 1622505600),  # Already in seconds
            (1622505600000, 1622505600),  # Milliseconds
            (1622505600000000, 1622505600),  # Microseconds
            ("1622505600", 1622505600),  # String integer
            ("2021-06-01T00:00:00Z", 1622505600),  # ISO string
            (datetime(2021, 6, 1, tzinfo=timezone.utc), 1622505600),  # Datetime
        ],
    )
    def test_normalize_timestamp(self, timestamp_raw, expected_seconds):
        """Test timestamp normalization with various input formats."""
        candle = CandleData(
            timestamp_raw=timestamp_raw,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
        )
        assert candle.timestamp == expected_seconds

    def test_normalize_timestamp_invalid_format(self):
        """Test timestamp normalization with invalid format."""
        with pytest.raises(ValueError):
            CandleData(
                timestamp_raw="not-a-timestamp",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000.0,
            )

    def test_to_array(self, sample_candle_data):
        """Test conversion to array format."""
        array = sample_candle_data.to_array()

        assert len(array) == 10
        assert array[0] == float(sample_candle_data.timestamp)
        assert array[1] == sample_candle_data.open
        assert array[2] == sample_candle_data.high
        assert array[3] == sample_candle_data.low
        assert array[4] == sample_candle_data.close
        assert array[5] == sample_candle_data.volume
        assert array[6] == sample_candle_data.quote_asset_volume
        assert array[7] == sample_candle_data.n_trades
        assert array[8] == sample_candle_data.taker_buy_base_volume
        assert array[9] == sample_candle_data.taker_buy_quote_volume

    def test_from_array(self):
        """Test creation from array format."""
        array = [
            1622505600.0,
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

        candle = CandleData.from_array(array)

        assert candle.timestamp == 1622505600
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        assert candle.n_trades == 1000
        assert candle.taker_buy_base_volume == 60.0
        assert candle.taker_buy_quote_volume == 3000000.0

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "timestamp": 1622505600,
            "open": 50000.0,
            "high": 51000.0,
            "low": 49000.0,
            "close": 50500.0,
            "volume": 100.0,
            "quote_asset_volume": 5000000.0,
            "n_trades": 1000,
            "taker_buy_base_volume": 60.0,
            "taker_buy_quote_volume": 3000000.0,
        }

        candle = CandleData.from_dict(data)

        assert candle.timestamp == 1622505600
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
        assert candle.n_trades == 1000
        assert candle.taker_buy_base_volume == 60.0
        assert candle.taker_buy_quote_volume == 3000000.0

    def test_from_dict_with_alternative_keys(self):
        """Test creation from dictionary with alternative keys."""
        data = {"t": 1622505600, "o": 50000.0, "h": 51000.0, "l": 49000.0, "c": 50500.0, "v": 100.0}

        candle = CandleData.from_dict(data)

        assert candle.timestamp == 1622505600
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0

    def test_from_dict_missing_required_field(self):
        """Test creation from dictionary with missing required field."""
        # Missing timestamp
        data = {"open": 50000.0, "high": 51000.0, "low": 49000.0, "close": 50500.0, "volume": 100.0}

        with pytest.raises(ValueError) as excinfo:
            CandleData.from_dict(data)

        assert "No timestamp found" in str(excinfo.value)

        # Missing price field
        data = {
            "timestamp": 1622505600,
            "high": 51000.0,
            "low": 49000.0,
            "close": 50500.0,
            "volume": 100.0,
        }

        with pytest.raises(ValueError) as excinfo:
            CandleData.from_dict(data)

        assert "No open value found" in str(excinfo.value)
