"""Data types for the hummingbot compatibility layer.

Provides configuration dataclasses and exceptions that mirror hummingbot's
candles connector interface, with no dependency on hummingbot itself.
"""

from dataclasses import dataclass


@dataclass
class CandlesConfig:
    """Configuration for a candles feed instance.

    :param connector_name: Exchange identifier (e.g., "binance_spot")
    :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
    :param interval: Candle interval string (e.g., "1m", "5m", "1h")
    :param max_records: Maximum number of candles to store
    """

    connector_name: str
    trading_pair: str
    interval: str = "1m"
    max_records: int = 500


@dataclass
class HistoricalCandlesConfig:
    """Configuration for fetching historical candles.

    :param connector_name: Exchange identifier
    :param trading_pair: Trading pair in standard format
    :param interval: Candle interval string
    :param start_time: Start timestamp in seconds
    :param end_time: End timestamp in seconds
    """

    connector_name: str
    trading_pair: str
    interval: str
    start_time: int
    end_time: int


class UnsupportedConnectorException(Exception):
    """Raised when a requested exchange connector is not supported.

    :param connector_name: The unsupported connector name
    """

    def __init__(self, connector_name: str) -> None:
        super().__init__(f"Connector '{connector_name}' is not supported.")
        self.connector_name = connector_name
