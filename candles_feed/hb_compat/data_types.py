"""Data types matching hummingbot's interface for candles configuration.

These types mirror hummingbot's HistoricalCandlesConfig to allow drop-in
compatibility without requiring hummingbot as a dependency.
"""

from dataclasses import dataclass


@dataclass
class HistoricalCandlesConfig:
    """Configuration for fetching historical candles.

    Mirrors hummingbot's HistoricalCandlesConfig for drop-in compatibility.

    :param connector_name: Exchange connector identifier (e.g., 'binance').
    :param trading_pair: Trading pair in standard format (e.g., 'BTC-USDT').
    :param interval: Candle interval string (e.g., '1m', '5m', '1h').
    :param start_time: Start timestamp in seconds (Unix epoch).
    :param end_time: End timestamp in seconds (Unix epoch).
    :param max_records: Maximum number of candle records to return.
    """

    connector_name: str
    trading_pair: str
    interval: str
    start_time: int = 0
    end_time: int = 0
    max_records: int = 500
