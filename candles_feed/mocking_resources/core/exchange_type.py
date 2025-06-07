"""
Exchange type definitions for the mock exchange framework.
"""

from enum import Enum


class ExchangeType(Enum):
    """
    Supported exchange types for mocking.

    This enum defines all the exchange types that can be simulated by the mock server.
    Each value corresponds to a specific exchange that has a corresponding adapter
    implementation in the candles feed package.
    """

    MOCK = "mock"
    BINANCE_SPOT = "binance_spot"
    BINANCE_PERPETUAL = "binance_perpetual"
    BYBIT_SPOT = "bybit_spot"
    BYBIT_PERPETUAL = "bybit_perpetual"
    COINBASE_ADVANCED_TRADE = "coinbase_advanced_trade"
    KRAKEN_SPOT = "kraken_spot"
    KUCOIN_SPOT = "kucoin_spot"
    KUCOIN_PERPETUAL = "kucoin_perpetual"
    OKX_SPOT = "okx_spot"
    OKX_PERPETUAL = "okx_perpetual"
    GATE_IO_SPOT = "gate_io_spot"
    GATE_IO_PERPETUAL = "gate_io_perpetual"
    MEXC_SPOT = "mexc_spot"
    MEXC_PERPETUAL = "mexc_perpetual"
    HYPERLIQUID_SPOT = "hyperliquid_spot"
    HYPERLIQUID_PERPETUAL = "hyperliquid_perpetual"
    ASCEND_EX_SPOT = "ascend_ex_spot"
