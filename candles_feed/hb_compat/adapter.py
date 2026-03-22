"""CandlesBaseAdapter — implements CandlesBaseProtocol by wrapping CandlesFeed.

This is the core translation layer between hummingbot's expected interface
and hb-candles-feed's native API. No hummingbot imports.
"""

import asyncio

import numpy as np
import pandas as pd

from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.hb_compat.data_types import HistoricalCandlesConfig

# Standard column order matching hummingbot's CandlesBase.columns
COLUMNS = [
    "timestamp", "open", "high", "low", "close", "volume",
    "quote_asset_volume", "n_trades",
    "taker_buy_base_volume", "taker_buy_quote_volume",
]


class CandlesBaseAdapter:
    """Adapter implementing hummingbot's CandlesBase interface via CandlesFeed.

    Precondition for start()/stop(): Must be called from within a running
    asyncio event loop (always true in hummingbot's runtime).
    """

    def __init__(
        self,
        exchange: str,
        trading_pair: str,
        interval: str = "1m",
        max_records: int = 500,
    ):
        self._feed = CandlesFeed(
            exchange=exchange,
            trading_pair=trading_pair,
            interval=interval,
            max_records=max_records,
        )

    # --- Properties delegating to CandlesFeed ---

    @property
    def name(self) -> str:
        """Exchange identifier."""
        return self._feed.exchange

    @property
    def interval(self) -> str:
        """Candle interval."""
        return self._feed.interval

    @property
    def max_records(self) -> int:
        """Maximum candle count."""
        return self._feed.max_records

    @property
    def ready(self) -> bool:
        """True when candle deque is full."""
        return self._feed.ready

    @property
    def candles_df(self) -> pd.DataFrame:
        """OHLCV data as DataFrame. Property, not method."""
        return self._feed.get_candles_df()

    @property
    def interval_in_seconds(self) -> int:
        """Interval duration in seconds."""
        return self._feed.interval_in_seconds

    # --- Sync lifecycle (bridge to async) ---

    def start(self) -> None:
        """Start the feed. Schedules async start on the running event loop."""
        loop = asyncio.get_running_loop()
        loop.create_task(self._feed.start())

    def stop(self) -> None:
        """Stop the feed. Schedules async stop on the running event loop."""
        loop = asyncio.get_running_loop()
        loop.create_task(self._feed.stop())

    # --- Data fetching ---

    async def fetch_candles(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> np.ndarray:
        """Fetch candles as numpy array (hummingbot's expected return type).

        :param start_time: Start timestamp in seconds (optional)
        :param end_time: End timestamp in seconds (optional)
        :param limit: Maximum candles to fetch; defaults to 500 if None
        :return: ndarray of shape (N, 10), dtype float
        """
        effective_limit = limit if limit is not None else 500
        candles = await self._feed.fetch_candles(
            start_time=start_time, end_time=end_time, limit=effective_limit
        )
        return self._candle_data_list_to_ndarray(candles)

    async def get_historical_candles(
        self, config: HistoricalCandlesConfig
    ) -> pd.DataFrame:
        """Get historical candles. Unpacks config, ignores redundant fields.

        :param config: Historical candles configuration
        :return: DataFrame with candle data
        """
        return await self._feed.get_historical_candles(
            start_time=config.start_time, end_time=config.end_time
        )

    # --- Trading pair ---

    def get_exchange_trading_pair(self, trading_pair: str) -> str:
        """Return exchange-formatted trading pair. Parameter ignored (set at init).

        :param trading_pair: Trading pair (unused; exchange pair set at construction)
        :return: Exchange-formatted trading pair string
        """
        return self._feed.ex_trading_pair

    # --- MarketDataProvider compatibility ---

    def reset_with_dataframe(self, df: pd.DataFrame) -> None:
        """Replace internal candle data from a DataFrame.

        Used by MarketDataProvider.get_historical_candles_df() instead of
        direct _candles deque manipulation.

        :param df: DataFrame with standard 10 columns. Empty clears candles.
        """
        self._feed._candles.clear()
        if df.empty:
            return
        for _, row in df.iterrows():
            candle = CandleData(
                timestamp_raw=int(row["timestamp"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                quote_asset_volume=float(row.get("quote_asset_volume", 0.0)),
                n_trades=int(row.get("n_trades", 0)),
                taker_buy_base_volume=float(row.get("taker_buy_base_volume", 0.0)),
                taker_buy_quote_volume=float(row.get("taker_buy_quote_volume", 0.0)),
            )
            self._feed.add_candle(candle)

    # --- Conversion helpers ---

    @staticmethod
    def _candle_data_list_to_ndarray(candles: list[CandleData]) -> np.ndarray:
        """Convert list[CandleData] to numpy array matching CandlesBase format.

        :param candles: List of CandleData objects
        :return: ndarray of shape (N, 10), dtype float
        """
        if not candles:
            return np.array([]).reshape(0, 10)
        return np.array(
            [
                [
                    c.timestamp, c.open, c.high, c.low, c.close, c.volume,
                    c.quote_asset_volume, c.n_trades,
                    c.taker_buy_base_volume, c.taker_buy_quote_volume,
                ]
                for c in candles
            ],
            dtype=float,
        )
