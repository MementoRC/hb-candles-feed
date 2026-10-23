"""
Core candles feed class for the Candle Feed framework.

This module provides the main class for managing candle data feeds.
"""

import asyncio
import logging
import typing
from collections import deque
from collections.abc import Iterable

import numpy as np
import pandas as pd

from candles_feed.core.candle_data import CandleData
from candles_feed.core.collection_strategies import (
    RESTPollingStrategy,
    WebSocketStrategy,
)
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.intervals import (
    floor_timestamp,
    is_valid_step,
    is_variable_length_interval,
    next_boundary,
)
from candles_feed.core.network_config import NetworkConfig
from candles_feed.core.protocols import (
    Logger,
)
from candles_feed.core.rate_limiter import RateLimitedNetworkClient, get_adapter_rate_limiter

HISTORICAL_MAX_ATTEMPTS = 3
HISTORICAL_RETRY_BASE_DELAY = 0.5  # seconds; doubles after each failed attempt
_MAX_LOGGED_GAPS = 5


class HistoricalCandlesError(Exception):
    """Raised when a historical page keeps failing, so the result would be silently truncated.

    :ivar partial: Candles fetched before the failure (same columns as normal output)
    :ivar failed_at: Start timestamp of the page that kept failing
    """

    def __init__(self, message: str, partial: pd.DataFrame, failed_at: int):
        super().__init__(message)
        self.partial = partial
        self.failed_at = failed_at


class CandlesFeed:
    """Main class that coordinates data collection from exchanges.

    This class is responsible for creating and managing the components needed
    to fetch and process candle data from exchanges.
    """

    def __init__(
        self,
        exchange: str,
        trading_pair: str,
        interval: str = "1m",
        max_records: int = 150,
        logger: Logger | None = None,
        hummingbot_components: dict | None = None,
        network_config: NetworkConfig | None = None,
    ):
        """Initialize the candles feed.

        :param exchange: Name of the exchange
        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param max_records: Maximum number of candles to store
        :param logger: Logger instance
        :param hummingbot_components: Optional dictionary containing Hummingbot components:
            - throttler: AsyncThrottlerBase instance
            - web_assistants_factory: WebAssistantsFactory instance
        :param network_config: Optional network configuration for testnet support
        """
        self.exchange = exchange
        self.trading_pair = trading_pair
        self.interval = interval
        self.max_records = max_records
        self.logger: Logger = (
            logger if logger is not None else typing.cast("Logger", logging.getLogger(__name__))
        )
        self._network_config = network_config

        # Get adapter from registry
        self._adapter = ExchangeRegistry.get_adapter_instance(
            exchange, network_config=network_config
        )
        self.ex_trading_pair = self._adapter.get_trading_pair_format(trading_pair)

        # Initialize components
        self._candles: deque[CandleData] = deque(maxlen=max_records)

        # Create the appropriate network client based on available components.
        # Imported locally to avoid a circular import: hb_compat's package
        # __init__ imports CandlesBaseAdapter, which imports CandlesFeed.
        from candles_feed.hb_compat.hummingbot_network_client_adapter import (
            NetworkClientFactory,
        )

        # All REST calls made through this client are paced by the adapter's shared limiter.
        self._network_client = RateLimitedNetworkClient(
            NetworkClientFactory.create_client(
                hummingbot_components=hummingbot_components, logger=self.logger
            ),
            get_adapter_rate_limiter(self._adapter),
        )
        self._network_client_context_entered = False
        self._data_processor = DataProcessor()

        # Strategy attributes
        self._rest_strategy = None
        self._ws_strategy = None
        self._active = False
        self._using_ws = False

        # Store the components for potential later use
        self._hummingbot_components = hummingbot_components

    def _create_ws_strategy(self):
        """Create a WebSocket strategy instance.

        This is a helper method that can be mocked in tests.
        """
        return WebSocketStrategy(
            network_client=self._network_client,
            adapter=self._adapter,
            trading_pair=self.trading_pair,
            interval=self.interval,
            data_processor=self._data_processor,
            candles_store=self._candles,
        )

    def _create_rest_strategy(self):
        """Create a REST polling strategy instance.

        This is a helper method that can be mocked in tests.
        """
        return RESTPollingStrategy(
            network_client=self._network_client,
            adapter=self._adapter,
            trading_pair=self.trading_pair,
            interval=self.interval,
            data_processor=self._data_processor,
            candles_store=self._candles,
        )

    async def start(self, strategy: str = "auto") -> None:
        """Start the feed.

        :param strategy: Strategy to use ("auto", "websocket", or "polling").
            "auto" uses websocket when the adapter supports it for the interval, otherwise
            REST polling. Polling latency is roughly max(interval / 2, 1) seconds.
        """
        if self._active:
            return

        # Ensure network client is properly initialized
        if not self._network_client_context_entered:
            await self._network_client.__aenter__()
            self._network_client_context_entered = True

        self.logger.debug(f"Starting candles feed for {self.trading_pair} on {self.exchange}")

        # Determine which strategy to use
        use_websocket = False

        if strategy == "auto":
            # Use websocket only if the adapter supports it for this interval;
            # REST-only adapters raise NotImplementedError.
            get_ws_intervals = getattr(self._adapter, "get_ws_supported_intervals", None)
            try:
                use_websocket = get_ws_intervals is not None and self.interval in get_ws_intervals()
            except NotImplementedError:
                use_websocket = False
            if not use_websocket:
                poll_seconds = max(self.interval_in_seconds / 2, 1)
                self.logger.info(
                    f"{self.exchange} has no websocket for {self.interval}; "
                    f"using REST polling every {poll_seconds:g}s"
                )
        elif strategy == "websocket":
            use_websocket = True
        elif strategy not in ["auto", "websocket", "rest", "polling"]:
            raise ValueError(
                f"Invalid strategy: {strategy}. Must be one of 'auto', 'websocket', 'rest', 'polling'"
            )

        # Create and start appropriate strategy
        if use_websocket:
            # Only create a new strategy if one doesn't exist already (for testing)
            if not self._ws_strategy:
                self._ws_strategy = self._create_ws_strategy()

            if not self._ws_strategy:
                raise ValueError("WebSocket strategy not supported by this adapter")

            await self._ws_strategy.start()
            self._using_ws = True
        else:
            # Only create a new strategy if one doesn't exist already (for testing)
            if not self._rest_strategy:
                self._rest_strategy = self._create_rest_strategy()

            if not self._rest_strategy:
                raise ValueError("REST strategy not supported by this adapter")

            await self._rest_strategy.start()
            self._using_ws = False

        self._active = True

    async def stop(self) -> None:
        """Stop the feed."""
        if not self._active:
            return

        self.logger.debug(f"Stopping candles feed for {self.trading_pair}")

        if self._using_ws and self._ws_strategy:
            await self._ws_strategy.stop()
        elif self._rest_strategy:
            await self._rest_strategy.stop()

        # Clean up network client resources using context manager pattern
        if self._network_client_context_entered:
            await self._network_client.__aexit__(None, None, None)
            self._network_client_context_entered = False

        self._active = False

    def get_candles(self) -> list[CandleData]:
        """Get the candles.

        :return: List of candle data objects
        """
        return list(self._candles)

    @property
    def max_candles_per_request(self) -> int:
        """Maximum number of candles the exchange returns per REST request.

        :return: The adapter's ``MAX_CANDLES_PER_REQUEST`` (500 if undefined)
        """
        return int(getattr(self._adapter, "MAX_CANDLES_PER_REQUEST", 500))

    def add_candle(self, candle: CandleData) -> None:
        """Add a candle to the feed manually.

        This is primarily used for testing.

        :param candle: Candle data to add
        """
        self._candles.append(candle)

    def replace_candles(self, candles: Iterable[CandleData]) -> None:
        """Replace all candles in one pass; keeps the newest ``max_records``.

        :param candles: Candles in chronological order
        """
        self._candles.clear()
        self._candles.extend(candles)

    def clear_candles(self) -> None:
        """Remove all candles from the feed.

        :return: None
        """
        self._candles.clear()

    def get_candles_df(self) -> pd.DataFrame:
        """Get candles as a pandas DataFrame.

        :return: DataFrame with candle data
        """
        return pd.DataFrame(
            [
                {
                    "timestamp": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                    "quote_asset_volume": c.quote_asset_volume,
                    "n_trades": c.n_trades,
                    "taker_buy_base_volume": c.taker_buy_base_volume,
                    "taker_buy_quote_volume": c.taker_buy_quote_volume,
                }
                for c in self._candles
            ]
        )

    async def fetch_candles(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 500,
    ) -> list[CandleData]:
        """Fetch historical candles with a single REST request.

        Results are returned without being written to the live candle store.

        :param start_time: Start time for fetching candles (timestamp in seconds)
        :param end_time: End time for fetching candles (timestamp in seconds)
        :param limit: Maximum number of candles to fetch
        :return: List of candle data
        """
        # Ensure network client is properly initialized for one-off requests
        if not self._network_client_context_entered:
            await self._network_client.__aenter__()
            self._network_client_context_entered = True

        # Use REST polling regardless of current strategy
        strategy = self._rest_strategy or self._create_rest_strategy()

        # Use poll_once which is the actual method implemented in RESTPollingStrategy
        return await strategy.poll_once(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def get_historical_candles(self, start_time: int, end_time: int) -> pd.DataFrame:
        """Get historical candles between start and end time (inclusive).

        Pages forward from start_time in chunks of the adapter's
        ``MAX_CANDLES_PER_REQUEST`` until end_time is reached, the exchange runs out of
        data, or pagination stops making progress. Results are returned without being
        written to the live candle store.

        :param start_time: Start time in seconds
        :param end_time: End time in seconds
        :return: DataFrame with candle data, ascending by timestamp
        """
        if not self._network_client_context_entered:
            await self._network_client.__aenter__()
            self._network_client_context_entered = True

        strategy = self._rest_strategy or self._create_rest_strategy()
        step = self.interval_in_seconds
        start_time = floor_timestamp(start_time, self.interval, step)
        end_time = floor_timestamp(end_time, self.interval, step)
        page_limit = self.max_candles_per_request
        max_pages = max(0, end_time - start_time) // (step * page_limit) + 3

        merged: dict[int, CandleData] = {}
        page_start = start_time
        for _ in range(max_pages):
            page = await self._fetch_historical_page(strategy, page_start, page_limit, merged)
            if not page:
                break
            for candle in page:
                if page_start <= candle.timestamp <= end_time:
                    merged[candle.timestamp] = candle
            last_ts = max(c.timestamp for c in page)
            if last_ts >= end_time or last_ts < page_start:
                break
            next_start = next_boundary(last_ts, self.interval, step)
            if next_start <= page_start:
                break
            page_start = next_start
        else:
            self.logger.warning(
                f"Historical candle pagination for {self.trading_pair} on {self.exchange} "
                f"hit the page cap ({max_pages}); result may be incomplete"
            )

        df = self._candles_to_df([merged[ts] for ts in sorted(merged)])
        gaps = self._find_gaps(df["timestamp"].tolist() if not df.empty else [], step)
        if gaps:
            shown = ", ".join(f"{a}->{b}" for a, b in gaps[:_MAX_LOGGED_GAPS])
            self.logger.warning(
                f"Historical candles for {self.trading_pair} on {self.exchange} contain "
                f"{len(gaps)} gap(s) (first: {shown}); exchange has no data there"
            )
        df.attrs["gaps"] = gaps
        return df

    async def _fetch_historical_page(
        self,
        strategy: RESTPollingStrategy,
        page_start: int,
        page_limit: int,
        merged: dict[int, CandleData],
    ) -> list[CandleData]:
        """Fetch one historical page, retrying transient failures with exponential backoff.

        :param strategy: REST strategy used for the request
        :param page_start: Start timestamp of the page in seconds
        :param page_limit: Maximum candles per page
        :param merged: Candles collected so far (used as partial result on failure)
        :return: Raw candles of the page; empty list means end of data
        :raises HistoricalCandlesError: If every attempt fails
        """
        last_exc: Exception | None = None
        for attempt in range(HISTORICAL_MAX_ATTEMPTS):
            try:
                return await strategy.fetch_rest_page(start_time=page_start, limit=page_limit)
            except Exception as e:
                last_exc = e
                if attempt < HISTORICAL_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(HISTORICAL_RETRY_BASE_DELAY * 2**attempt)
        self.logger.error(
            f"Historical candle fetch for {self.trading_pair} on {self.exchange} failed at "
            f"{page_start} after {HISTORICAL_MAX_ATTEMPTS} attempts: {last_exc!r}"
        )
        raise HistoricalCandlesError(
            f"Failed fetching historical candles at {page_start}: {last_exc!r}",
            partial=self._candles_to_df([merged[ts] for ts in sorted(merged)]),
            failed_at=page_start,
        ) from last_exc

    def _find_gaps(self, timestamps: list[int], step: int) -> list[tuple[int, int]]:
        """Return (previous, next) timestamp pairs that are not consecutive candles.

        :param timestamps: Ascending candle timestamps
        :param step: Nominal interval length in seconds
        :return: List of gap boundaries
        """
        return [
            (prev, nxt)
            for prev, nxt in zip(timestamps, timestamps[1:], strict=False)
            if not is_valid_step(prev, nxt, self.interval, step)
        ]

    @staticmethod
    def _candles_to_df(candles: list[CandleData]) -> pd.DataFrame:
        """Convert candles to a DataFrame with the standard columns.

        :param candles: Candles to convert
        :return: DataFrame (``attrs["gaps"]`` set to an empty list)
        """
        df = pd.DataFrame(
            [
                {
                    "timestamp": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                    "quote_asset_volume": c.quote_asset_volume,
                    "n_trades": c.n_trades,
                    "taker_buy_base_volume": c.taker_buy_base_volume,
                    "taker_buy_quote_volume": c.taker_buy_quote_volume,
                }
                for c in candles
            ]
        )
        df.attrs["gaps"] = []
        return df

    @property
    def ready(self) -> bool:
        """Check if the feed has filled its candle history.

        :return: True if candles deque is full, False otherwise
        """
        return len(self._candles) == self._candles.maxlen

    @property
    def first_timestamp(self) -> int | None:
        """Return the timestamp of the oldest candle.

        :return: Timestamp of the first candle, or None if empty
        """
        if not self._candles:
            return None
        return self._candles[0].timestamp

    @property
    def last_timestamp(self) -> int | None:
        """Return the timestamp of the newest candle.

        :return: Timestamp of the last candle, or None if empty
        """
        if not self._candles:
            return None
        return self._candles[-1].timestamp

    @property
    def interval_in_seconds(self) -> int:
        """Return the interval duration in seconds.

        :return: Number of seconds in the configured interval
        """
        return self._adapter.get_supported_intervals()[self.interval]

    def _round_timestamp_to_interval_multiple(self, timestamp: int) -> int:
        """Round timestamp to nearest interval boundary.

        :param timestamp: Timestamp in seconds
        :return: Rounded timestamp
        """
        interval_seconds = self._adapter.get_supported_intervals()[self.interval]
        return floor_timestamp(int(timestamp), self.interval, interval_seconds)

    def check_candles_sorted_and_equidistant(self, candles_data=None) -> bool:
        """Check if candles are sorted by timestamp and have equal intervals.

        :param candles_data: Optional candle data to check (defaults to internal candles)
        :return: True if candles are valid, False otherwise
        """
        if candles_data is None:
            if len(self._candles) <= 1:
                return True
            candles_data = [
                [c.timestamp, c.open, c.high, c.low, c.close, c.volume] for c in self._candles
            ]

        candles = np.array(candles_data)
        if len(candles) <= 1:
            return True

        # Check timestamps are sorted
        timestamps = candles[:, 0].astype(float)
        if not np.all(np.diff(timestamps) >= 0):
            self.logger.warning("Candles are not sorted by timestamp in ascending order")
            return False

        # Check intervals are consistent
        timestamp_diffs = np.diff(timestamps)
        if len(timestamp_diffs) > 0:
            unique_diffs = np.unique(timestamp_diffs)
            interval_seconds = self._adapter.get_supported_intervals()[self.interval]
            if is_variable_length_interval(self.interval):
                equidistant = all(
                    is_valid_step(int(a), int(b), self.interval, interval_seconds)
                    for a, b in zip(timestamps[:-1], timestamps[1:], strict=True)
                )
            else:
                equidistant = bool(np.all(np.isclose(unique_diffs, interval_seconds, rtol=1e-5)))
            if not equidistant:
                self.logger.warning("Candles do not have equal intervals")
                return False

        return True
