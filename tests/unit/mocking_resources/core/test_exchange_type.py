"""
Unit tests for the ExchangeType enum in mocking_resources.
"""

from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class TestExchangeType:
    """Tests for the ExchangeType enum."""

    def test_enum_values(self):
        """Test that the enum has the expected values."""
        # Spot exchanges
        assert ExchangeType.BINANCE_SPOT.value == "binance_spot"
        assert ExchangeType.BYBIT_SPOT.value == "bybit_spot"
        assert ExchangeType.COINBASE_ADVANCED_TRADE.value == "coinbase_advanced_trade"
        assert ExchangeType.KRAKEN_SPOT.value == "kraken_spot"
        assert ExchangeType.KUCOIN_SPOT.value == "kucoin_spot"
        assert ExchangeType.OKX_SPOT.value == "okx_spot"
        assert ExchangeType.GATE_IO_SPOT.value == "gate_io_spot"
        assert ExchangeType.MEXC_SPOT.value == "mexc_spot"
        assert ExchangeType.HYPERLIQUID_SPOT.value == "hyperliquid_spot"
        assert ExchangeType.ASCEND_EX_SPOT.value == "ascend_ex_spot"

        # Perpetual exchanges
        assert ExchangeType.BINANCE_PERPETUAL.value == "binance_perpetual"
        assert ExchangeType.BYBIT_PERPETUAL.value == "bybit_perpetual"
        assert ExchangeType.KUCOIN_PERPETUAL.value == "kucoin_perpetual"
        assert ExchangeType.OKX_PERPETUAL.value == "okx_perpetual"
        assert ExchangeType.GATE_IO_PERPETUAL.value == "gate_io_perpetual"
        assert ExchangeType.MEXC_PERPETUAL.value == "mexc_perpetual"
        assert ExchangeType.HYPERLIQUID_PERPETUAL.value == "hyperliquid_perpetual"

    def test_access_by_name(self):
        """Test accessing enum values by name."""
        assert ExchangeType["BINANCE_SPOT"] == ExchangeType.BINANCE_SPOT
        assert ExchangeType["BYBIT_PERPETUAL"] == ExchangeType.BYBIT_PERPETUAL

    def test_iteration(self):
        """Test that we can iterate over the enum."""
        count = 0
        for exchange_type in ExchangeType:
            assert isinstance(exchange_type, ExchangeType)
            count += 1

        # Make sure we have the expected number of exchange types
        # Update this if more exchanges are added
        assert count == 18
