"""Hummingbot-compatible data types.

These classes mirror hummingbot's CandlesConfig and HistoricalCandlesConfig
exactly (field names, types, defaults). No hummingbot import.
"""

from pydantic import BaseModel


class CandlesConfig(BaseModel):
    """Configuration for a candle feed. Matches hummingbot's CandlesConfig."""

    connector: str
    trading_pair: str
    interval: str = "1m"
    max_records: int = 500


class HistoricalCandlesConfig(BaseModel):
    """Configuration for historical candle requests. Matches hummingbot's HistoricalCandlesConfig."""

    connector_name: str
    trading_pair: str
    interval: str
    start_time: int
    end_time: int


class UnsupportedConnectorException(Exception):
    """Raised when a connector is not supported by hb-candles-feed."""

    def __init__(self, connector: str):
        self.connector = connector
        super().__init__(
            f"Connector '{connector}' is not supported by hb-candles-feed."
        )
