"""Protocol definitions for the hummingbot compatibility layer.

Defines structural subtypes (Protocols) that match hummingbot's candles
connector interface, enabling static type checking without hummingbot imports.
"""

from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd

from candles_feed.hb_compat.data_types import HistoricalCandlesConfig


@runtime_checkable
class CandlesBaseProtocol(Protocol):
    """Structural interface matching hummingbot's CandlesBase.

    Any object with these properties/methods satisfies this protocol
    without needing to inherit from it.
    """

    @property
    def name(self) -> str:
        """Exchange identifier."""
        ...

    @property
    def interval(self) -> str:
        """Candle interval string."""
        ...

    @property
    def max_records(self) -> int:
        """Maximum candle count."""
        ...

    @property
    def ready(self) -> bool:
        """True when the candle history is full."""
        ...

    @property
    def candles_df(self) -> pd.DataFrame:
        """OHLCV candle data as a DataFrame."""
        ...

    @property
    def interval_in_seconds(self) -> int:
        """Interval duration in seconds."""
        ...

    def start(self) -> None:
        """Start the candles feed."""
        ...

    def stop(self) -> None:
        """Stop the candles feed."""
        ...

    async def fetch_candles(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> np.ndarray:
        """Fetch candles as a numpy array."""
        ...

    async def get_historical_candles(
        self, config: HistoricalCandlesConfig
    ) -> pd.DataFrame:
        """Get historical candles from config."""
        ...

    def get_exchange_trading_pair(self, trading_pair: str) -> str:
        """Return exchange-formatted trading pair."""
        ...
