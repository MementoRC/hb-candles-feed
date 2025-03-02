"""
Unit tests for the ExchangeType enum.
"""

import unittest

from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType


class TestExchangeType(unittest.TestCase):
    """Tests for the ExchangeType enum."""
    
    def test_enum_values(self):
        """Test that the enum has the expected values."""
        # Spot exchanges
        self.assertEqual(ExchangeType.BINANCE_SPOT.value, "binance_spot")
        self.assertEqual(ExchangeType.BYBIT_SPOT.value, "bybit_spot")
        self.assertEqual(ExchangeType.COINBASE_ADVANCED_TRADE.value, "coinbase_advanced_trade")
        self.assertEqual(ExchangeType.KRAKEN_SPOT.value, "kraken_spot")
        self.assertEqual(ExchangeType.KUCOIN_SPOT.value, "kucoin_spot")
        self.assertEqual(ExchangeType.OKX_SPOT.value, "okx_spot")
        self.assertEqual(ExchangeType.GATE_IO_SPOT.value, "gate_io_spot")
        self.assertEqual(ExchangeType.MEXC_SPOT.value, "mexc_spot")
        self.assertEqual(ExchangeType.HYPERLIQUID_SPOT.value, "hyperliquid_spot")
        self.assertEqual(ExchangeType.ASCEND_EX_SPOT.value, "ascend_ex_spot")
        
        # Perpetual exchanges
        self.assertEqual(ExchangeType.BINANCE_PERPETUAL.value, "binance_perpetual")
        self.assertEqual(ExchangeType.BYBIT_PERPETUAL.value, "bybit_perpetual")
        self.assertEqual(ExchangeType.KUCOIN_PERPETUAL.value, "kucoin_perpetual")
        self.assertEqual(ExchangeType.OKX_PERPETUAL.value, "okx_perpetual")
        self.assertEqual(ExchangeType.GATE_IO_PERPETUAL.value, "gate_io_perpetual")
        self.assertEqual(ExchangeType.MEXC_PERPETUAL.value, "mexc_perpetual")
        self.assertEqual(ExchangeType.HYPERLIQUID_PERPETUAL.value, "hyperliquid_perpetual")
    
    def test_access_by_name(self):
        """Test accessing enum values by name."""
        self.assertEqual(ExchangeType.BINANCE_SPOT, ExchangeType['BINANCE_SPOT'])
        self.assertEqual(ExchangeType.BYBIT_PERPETUAL, ExchangeType['BYBIT_PERPETUAL'])
    
    def test_iteration(self):
        """Test that we can iterate over the enum."""
        count = 0
        for exchange_type in ExchangeType:
            self.assertIsInstance(exchange_type, ExchangeType)
            count += 1
        
        # Make sure we have the expected number of exchange types
        # Update this if more exchanges are added
        self.assertEqual(count, 17)


if __name__ == '__main__':
    unittest.main()