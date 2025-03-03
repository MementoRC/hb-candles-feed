"""
Unit tests for the CandleData class in testing_resources.
"""

import unittest
import time
from dataclasses import asdict

from candles_feed.testing_resources.candle_data_factory import CandleDataFactory
from candles_feed.core.candle_data import CandleData


class TestCandleData(unittest.TestCase):
    """Tests for the CandleData class."""
    
    def test_create_random_no_previous(self):
        """Test creating a random candle without a previous candle."""
        # Arrange
        timestamp = int(time.time())
        base_price = 50000.0
        volatility = 0.01
        
        # Act
        candle = CandleDataFactory.create_random(
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
        prev_candle = CandleData(
            timestamp_raw=prev_timestamp,
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
        candle = CandleDataFactory.create_random(
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
        candle = CandleData(
            timestamp_raw=timestamp,
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
    
    def test_from_dict(self):
        """Test creating a CandleData from a dictionary."""
        # Arrange - create a dictionary with candle data
        candle_dict = {
            'timestamp': 1613677200,
            'open': 50000.0,
            'high': 50500.0,
            'low': 49500.0,
            'close': 50200.0,
            'volume': 10.0,
            'quote_asset_volume': 500000.0,
            'n_trades': 100,
            'taker_buy_base_volume': 5.0,
            'taker_buy_quote_volume': 250000.0
        }
        
        # Act
        candle = CandleData.from_dict(candle_dict)
        
        # Assert
        self.assertEqual(candle.timestamp, candle_dict['timestamp'])
        self.assertEqual(candle.open, candle_dict['open'])
        self.assertEqual(candle.high, candle_dict['high'])
        self.assertEqual(candle.low, candle_dict['low'])
        self.assertEqual(candle.close, candle_dict['close'])
        self.assertEqual(candle.volume, candle_dict['volume'])
        self.assertEqual(candle.quote_asset_volume, candle_dict['quote_asset_volume'])
        self.assertEqual(candle.n_trades, candle_dict['n_trades'])
        self.assertEqual(candle.taker_buy_base_volume, candle_dict['taker_buy_base_volume'])
        self.assertEqual(candle.taker_buy_quote_volume, candle_dict['taker_buy_quote_volume'])
    
    def test_create_trending_series(self):
        """Test creating a trending series of candles."""
        # Arrange
        start_timestamp = int(time.time())
        count = 5
        interval_seconds = 60
        start_price = 50000.0
        trend = 0.001  # 0.1% up trend
        
        # Act
        candles = CandleDataFactory.create_trending_series(
            start_timestamp=start_timestamp,
            count=count,
            interval_seconds=interval_seconds,
            start_price=start_price,
            trend=trend
        )
        
        # Assert
        self.assertEqual(len(candles), count)
        self.assertEqual(candles[0].timestamp, start_timestamp)
        
        # Check that timestamps are sequentially increasing
        for i in range(1, count):
            self.assertEqual(candles[i].timestamp, start_timestamp + (i * interval_seconds))
        
        # First candle should be near the start price
        self.assertAlmostEqual(candles[0].open, start_price, delta=start_price * 0.1)

        # Just verify structure is correct - we can't easily test randomized prices
        # due to the volatility factor 
        self.assertIsNotNone(candles[-1].close)


if __name__ == '__main__':
    unittest.main()