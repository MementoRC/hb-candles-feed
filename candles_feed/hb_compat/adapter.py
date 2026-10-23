"""CandlesBaseAdapter — implements CandlesBaseProtocol by wrapping CandlesFeed.

This is the core translation layer between hummingbot's expected interface
and hb-candles-feed's native API. No hummingbot imports.
"""

import asyncio
import copy
import logging
from typing import ClassVar

import numpy as np
import pandas as pd

from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.hb_compat.data_types import HistoricalCandlesConfig
from candles_feed.utils.time_utils import ensure_timestamp_in_seconds

logger = logging.getLogger(__name__)

# Standard column order matching hummingbot's CandlesBase.columns
COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_asset_volume",
    "n_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]


def _to_compat_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Shape a frame to the hummingbot contract: the 10 columns in order, all float64.

    ``df.attrs`` (e.g. the ``gaps`` list from historical fetches) is carried over.
    """
    out = df.reindex(columns=COLUMNS).astype(float)
    out.attrs = copy.deepcopy(df.attrs)
    return out


def _safe_float(value: float | int | str | None, default: float = 0.0) -> float:
    """Convert value to float, returning default for NaN/None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return float(value)


def _safe_int(value: float | int | str | None, default: int = 0) -> int:
    """Convert value to int, returning default for NaN/None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return int(value)


# Attribute names on CandleData corresponding to COLUMNS order.
_CANDLE_ATTRS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_asset_volume",
    "n_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]
assert _CANDLE_ATTRS == COLUMNS, "COLUMNS and _CANDLE_ATTRS must match"


class CandlesBaseAdapter:
    """Adapter implementing hummingbot's CandlesBase interface via CandlesFeed.

    Precondition for start()/stop(): Must be called from within a running
    asyncio event loop (always true in hummingbot's runtime).
    """

    # Class-level upstream names (CandlesBase.interval_to_seconds / columns /
    # ensure_timestamp_in_seconds). Plain dict: no bidict dependency.
    interval_to_seconds: ClassVar[dict[str, int]] = {
        "1s": 1,
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "6h": 21600,
        "8h": 28800,
        "12h": 43200,
        "1d": 86400,
        "3d": 259200,
        "1w": 604800,
        "1M": 2592000,
    }
    columns: ClassVar[list[str]] = list(COLUMNS)
    ensure_timestamp_in_seconds = staticmethod(ensure_timestamp_in_seconds)

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
        self._start_task: asyncio.Task | None = None
        self._stop_task: asyncio.Task | None = None
        self._last_task_error: BaseException | None = None

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
        return _to_compat_frame(self._feed.get_candles_df())

    @property
    def interval_in_seconds(self) -> int:
        """Interval duration in seconds."""
        return self._feed.interval_in_seconds

    # --- Sync lifecycle (bridge to async) ---

    @property
    def last_task_error(self) -> BaseException | None:
        """Exception from the most recent start/stop task, or None.

        Cancelled tasks are not errors. Reset to None when a new start()/stop()
        is scheduled.
        """
        return self._last_task_error

    def _track_task(self, task: asyncio.Task) -> None:
        """Done-callback: log and record a failure of a start/stop task."""
        if task.cancelled():
            return
        if (exc := task.exception()) is not None:
            self._last_task_error = exc
            logger.error("CandlesFeed task failed: %r", exc, exc_info=exc)

    def start(self) -> None:
        """Start the feed. Schedules async start on the running event loop.

        A no-op while a previous start task is still pending (no duplicate task).
        """
        if self._start_task is not None and not self._start_task.done():
            return
        loop = asyncio.get_running_loop()
        self._last_task_error = None
        self._start_task = loop.create_task(self._feed.start())
        self._start_task.add_done_callback(self._track_task)

    def stop(self) -> None:
        """Stop the feed. Schedules async stop on the running event loop.

        Mirrors upstream ``CandlesBase.stop_network``, which cancels the pending
        listen task: a still-pending start task is cancelled so the feed cannot
        finish starting after stop(), then the feed's own stop() runs to release
        any partially acquired resources. Safe to call before start().
        """
        loop = asyncio.get_running_loop()
        if self._start_task is not None and not self._start_task.done():
            self._start_task.cancel()
        self._start_task = None
        self._last_task_error = None
        self._stop_task = loop.create_task(self._feed.stop())
        self._stop_task.add_done_callback(self._track_task)

    # --- Data fetching ---

    async def fetch_candles(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> np.ndarray:
        """Fetch candles as numpy array (hummingbot's expected return type).

        Results are returned only; they are not stored in ``candles_df``.

        :param start_time: Start timestamp in seconds (optional if end_time given)
        :param end_time: End timestamp in seconds (optional if start_time given)
        :param limit: Maximum candles to fetch; defaults to the exchange maximum per
            request and is clamped to [1, exchange maximum]
        :return: ndarray of shape (N, 10), dtype float
        :raises ValueError: If neither start_time nor end_time is given
        """
        if start_time is None and end_time is None:
            raise ValueError("Either the start time or end time must be specified.")
        max_per_request = self._feed.max_candles_per_request
        if limit is None:
            limit = max_per_request
        effective_limit = min(max_per_request, max(limit, 1))
        candles = await self._feed.fetch_candles(
            start_time=start_time, end_time=end_time, limit=effective_limit
        )
        return self._candle_data_list_to_ndarray(candles)

    async def get_historical_candles(self, config: HistoricalCandlesConfig) -> pd.DataFrame:
        """Get historical candles. Unpacks config, ignores redundant fields.

        :param config: Historical candles configuration
        :return: DataFrame with candle data
        """
        df = await self._feed.get_historical_candles(
            start_time=config.start_time, end_time=config.end_time
        )
        return _to_compat_frame(df)

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
        self._feed.clear_candles()
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
                quote_asset_volume=_safe_float(row.get("quote_asset_volume", 0.0)),
                n_trades=_safe_int(row.get("n_trades", 0)),
                taker_buy_base_volume=_safe_float(row.get("taker_buy_base_volume", 0.0)),
                taker_buy_quote_volume=_safe_float(row.get("taker_buy_quote_volume", 0.0)),
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
            return np.array([]).reshape(0, len(COLUMNS))
        return np.array(
            [[getattr(c, attr) for attr in _CANDLE_ATTRS] for c in candles],
            dtype=float,
        )
