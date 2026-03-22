# candles_feed/hb_compat/protocols.py
"""Protocol defining hummingbot's expected CandlesBase interface.

This protocol captures what MarketDataProvider actually calls on candle feed objects.
"""

from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd

from candles_feed.hb_compat.data_types import HistoricalCandlesConfig


@runtime_checkable
class CandlesBaseProtocol(Protocol):
    """Interface contract that hummingbot's MarketDataProvider expects.

    Only includes methods and properties that MarketDataProvider actually uses.
    """

    @property
    def name(self) -> str:
        """Exchange identifier."""
        ...

    @property
    def interval(self) -> str:
        """Candle interval (e.g., '1m', '5m')."""
        ...

    @property
    def max_records(self) -> int:
        """Maximum number of candles stored."""
        ...

    @property
    def ready(self) -> bool:
        """True when candle deque is full."""
        ...

    @property
    def candles_df(self) -> pd.DataFrame:
        """OHLCV data as a DataFrame."""
        ...

    @property
    def interval_in_seconds(self) -> int:
        """Interval duration in seconds."""
        ...

    def start(self) -> None:
        """Start the candle feed (synchronous)."""
        ...

    def stop(self) -> None:
        """Stop the candle feed (synchronous)."""
        ...

    async def fetch_candles(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> np.ndarray:
        """Fetch candles as numpy array."""
        ...

    async def get_historical_candles(
        self, config: HistoricalCandlesConfig
    ) -> pd.DataFrame:
        """Get historical candles using config object."""
        ...

    def get_exchange_trading_pair(self, trading_pair: str) -> str:
        """Get exchange-specific trading pair format."""
        ...
