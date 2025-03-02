"""
Unit tests for the MockCandleData class.
"""

import unittest
import time
from dataclasses import asdict

from candles_feed.testing_resources.mocks.core.candle_data import MockCandleData


class TestMockCandleData(unittest.TestCase):
    """Tests for the MockCandleData class."""
    
    def test_create_random_no_previous(self):
        """Test creating a random candle without a previous candle."""
        # Arrange
        timestamp = int(time.time())
        base_price = 50000.0
        volatility = 0.01
        
        # Act
        candle = MockCandleData.create_random(
            timestamp=timestamp,
            base_price=base_price,
            volatility=volatility
        )
        
        # Assert
        self.assertEqual(candle.timestamp, timestamp)
        self.assertEqual(candle.open, base_price)
        self.assertGreaterEqual(candle.high, max(candle.open, candle.close))
        self.assertLessEqual(candle.low, min(candle.open, candle.close))
        self.assertGreater(candle.volume, 0)
        self.assertGreater(candle.quote_asset_volume, 0)
        self.assertGreater(candle.n_trades, 0)
        self.assertGreater(candle.taker_buy_base_volume, 0)
        self.assertGreater(candle.taker_buy_quote_volume, 0)
    
    def test_create_random_with_previous(self):
        """Test creating a random candle based on a previous candle."""
        # Arrange
        timestamp = int(time.time())
        prev_timestamp = timestamp - 60
        prev_candle = MockCandleData(
            timestamp=prev_timestamp,
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50200.0,
            volume=10.0,
            quote_asset_volume=500000.0,
            n_trades=100,
            taker_buy_base_volume=5.0,
            taker_buy_quote_volume=250000.0
        )
        
        # Act
        candle = MockCandleData.create_random(
            timestamp=timestamp,
            previous_candle=prev_candle,
            volatility=0.01
        )
        
        # Assert
        self.assertEqual(candle.timestamp, timestamp)
        self.assertEqual(candle.open, prev_candle.close)  # Open should be previous close
        self.assertGreaterEqual(candle.high, max(candle.open, candle.close))
        self.assertLessEqual(candle.low, min(candle.open, candle.close))
        self.assertGreater(candle.volume, 0)
        self.assertGreater(candle.quote_asset_volume, 0)
        self.assertGreater(candle.n_trades, 0)
        self.assertGreater(candle.taker_buy_base_volume, 0)
        self.assertGreater(candle.taker_buy_quote_volume, 0)
    
    def test_timestamp_ms_property(self):
        """Test the timestamp_ms property."""
        # Arrange
        timestamp = 1613677200  # 2021-02-19 00:00:00 UTC
        candle = MockCandleData(
            timestamp=timestamp,
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50200.0,
            volume=10.0,
            quote_asset_volume=500000.0,
            n_trades=100,
            taker_buy_base_volume=5.0,
            taker_buy_quote_volume=250000.0
        )
        
        # Act
        timestamp_ms = candle.timestamp_ms
        
        # Assert
        self.assertEqual(timestamp_ms, timestamp * 1000)
        self.assertEqual(timestamp_ms, 1613677200000)
    
    def test_from_candle_data(self):
        """Test creating a MockCandleData from another candle data object."""
        # Arrange - create a simple object with the required attributes
        class SampleCandleData:
            def __init__(self):
                self.timestamp = 1613677200
                self.open = 50000.0
                self.high = 50500.0
                self.low = 49500.0
                self.close = 50200.0
                self.volume = 10.0
                self.quote_asset_volume = 500000.0
                self.n_trades = 100
                self.taker_buy_base_volume = 5.0
                self.taker_buy_quote_volume = 250000.0
        
        sample_candle = SampleCandleData()
        
        # Act
        candle = MockCandleData.from_candle_data(sample_candle)
        
        # Assert
        self.assertEqual(candle.timestamp, sample_candle.timestamp)
        self.assertEqual(candle.open, sample_candle.open)
        self.assertEqual(candle.high, sample_candle.high)
        self.assertEqual(candle.low, sample_candle.low)
        self.assertEqual(candle.close, sample_candle.close)
        self.assertEqual(candle.volume, sample_candle.volume)
        self.assertEqual(candle.quote_asset_volume, sample_candle.quote_asset_volume)
        self.assertEqual(candle.n_trades, sample_candle.n_trades)
        self.assertEqual(candle.taker_buy_base_volume, sample_candle.taker_buy_base_volume)
        self.assertEqual(candle.taker_buy_quote_volume, sample_candle.taker_buy_quote_volume)
    
    def test_from_candle_data_missing_attrs(self):
        """Test creating a MockCandleData from an object with missing attributes."""
        # Arrange - create an object with missing attributes
        class PartialCandleData:
            def __init__(self):
                self.close = 50200.0  # Only has close price
        
        partial_candle = PartialCandleData()
        
        # Act
        candle = MockCandleData.from_candle_data(partial_candle)
        
        # Assert
        self.assertIsInstance(candle, MockCandleData)
        self.assertEqual(candle.close, partial_candle.close)
        # Other fields should have been randomly generated
        self.assertGreater(candle.volume, 0)


if __name__ == '__main__':
    unittest.main()