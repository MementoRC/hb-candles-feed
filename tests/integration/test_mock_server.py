"""
Integration tests for the mock exchange server.
"""

import asyncio
import unittest
import pytest

from candles_feed.testing_resources.mocks import ExchangeType, create_mock_server, MockCandleData


class TestMockExchangeServer(unittest.TestCase):
    """Integration tests for the mock exchange server."""
    
    @pytest.mark.asyncio
    async def test_create_and_start_server(self):
        """Test creating and starting a mock server."""
        # Create a mock server
        server = create_mock_server(
            exchange_type=ExchangeType.BINANCE_SPOT,
            host='127.0.0.1',
            port=8080
        )
        
        # Verify the server
        self.assertIsNotNone(server)
        self.assertEqual(server.exchange_type, ExchangeType.BINANCE_SPOT)
        self.assertEqual(server.host, '127.0.0.1')
        self.assertEqual(server.port, 8080)
        
        # Check default trading pairs
        self.assertEqual(len(server.trading_pairs), 3)
        self.assertIn('BTCUSDT_1m', server.trading_pairs)
        self.assertIn('ETHUSDT_1m', server.trading_pairs)
        self.assertIn('SOLUSDT_1m', server.trading_pairs)
        
        # Start the server
        url = await server.start()
        self.assertEqual(url, 'http://127.0.0.1:8080')
        
        # Stop the server
        await server.stop()
    
    @pytest.mark.asyncio
    async def test_create_server_with_custom_trading_pairs(self):
        """Test creating a server with custom trading pairs."""
        # Create a mock server with custom trading pairs
        trading_pairs = [
            ('BTCUSDT', '5m', 50000.0),
            ('ETHUSDT', '15m', 3000.0),
            ('DOGEUSDT', '1h', 0.1)
        ]
        
        server = create_mock_server(
            exchange_type=ExchangeType.BINANCE_SPOT,
            host='127.0.0.1',
            port=8080,
            trading_pairs=trading_pairs
        )
        
        # Verify the server
        self.assertIsNotNone(server)
        
        # Check trading pairs
        self.assertEqual(len(server.trading_pairs), 3)
        self.assertIn('BTCUSDT_5m', server.trading_pairs)
        self.assertIn('ETHUSDT_15m', server.trading_pairs)
        self.assertIn('DOGEUSDT_1h', server.trading_pairs)
        
        # Verify trading pair prices
        self.assertEqual(server.trading_pairs['BTCUSDT_5m'], 50000.0)
        self.assertEqual(server.trading_pairs['ETHUSDT_15m'], 3000.0)
        self.assertEqual(server.trading_pairs['DOGEUSDT_1h'], 0.1)
        
        # Start and stop the server
        await server.start()
        await server.stop()
    
    def test_mock_candle_data(self):
        """Test the MockCandleData class."""
        # Create a mock candle
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
        
        # Verify the candle
        self.assertEqual(candle.timestamp, timestamp)
        self.assertEqual(candle.open, 50000.0)
        self.assertEqual(candle.high, 50500.0)
        self.assertEqual(candle.low, 49500.0)
        self.assertEqual(candle.close, 50200.0)
        self.assertEqual(candle.volume, 10.0)
        self.assertEqual(candle.quote_asset_volume, 500000.0)
        self.assertEqual(candle.n_trades, 100)
        self.assertEqual(candle.taker_buy_base_volume, 5.0)
        self.assertEqual(candle.taker_buy_quote_volume, 250000.0)
        
        # Check timestamp_ms property
        self.assertEqual(candle.timestamp_ms, timestamp * 1000)
    
    def test_create_random_candle(self):
        """Test creating a random candle."""
        # Create a random candle
        timestamp = 1613677200  # 2021-02-19 00:00:00 UTC
        candle = MockCandleData.create_random(
            timestamp=timestamp,
            base_price=50000.0,
            volatility=0.01
        )
        
        # Verify the candle
        self.assertEqual(candle.timestamp, timestamp)
        self.assertEqual(candle.open, 50000.0)  # Initial base price
        self.assertGreater(candle.high, max(candle.open, candle.close))  # High should be higher than both open and close
        self.assertLess(candle.low, min(candle.open, candle.close))  # Low should be lower than both open and close
        self.assertGreater(candle.volume, 0)
        self.assertGreater(candle.quote_asset_volume, 0)
        self.assertGreater(candle.n_trades, 0)
        self.assertGreater(candle.taker_buy_base_volume, 0)
        self.assertGreater(candle.taker_buy_quote_volume, 0)
    
    def test_create_candle_from_previous(self):
        """Test creating a candle based on a previous candle."""
        # Create base candle
        base_timestamp = 1613677200  # 2021-02-19 00:00:00 UTC
        prev_candle = MockCandleData(
            timestamp=base_timestamp,
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
        
        # Create new candle based on previous
        new_timestamp = base_timestamp + 60  # 1 minute later
        new_candle = MockCandleData.create_random(
            timestamp=new_timestamp,
            previous_candle=prev_candle,
            volatility=0.01
        )
        
        # Verify the new candle
        self.assertEqual(new_candle.timestamp, new_timestamp)
        self.assertEqual(new_candle.open, prev_candle.close)  # Open should be previous close
        self.assertGreater(new_candle.high, max(new_candle.open, new_candle.close))
        self.assertLess(new_candle.low, min(new_candle.open, new_candle.close))
        self.assertGreater(new_candle.volume, 0)
        self.assertGreater(new_candle.quote_asset_volume, 0)
        self.assertGreater(new_candle.n_trades, 0)
        self.assertGreater(new_candle.taker_buy_base_volume, 0)
        self.assertGreater(new_candle.taker_buy_quote_volume, 0)


if __name__ == '__main__':
    unittest.main()
