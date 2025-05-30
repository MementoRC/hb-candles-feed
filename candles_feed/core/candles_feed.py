"""
Core candles feed class for the Candle Feed framework.

This module provides the main class for managing candle data feeds.
"""

import logging
from collections import deque
from typing import Deque

import numpy as np
import pandas as pd

from candles_feed.core.candle_data import CandleData
from candles_feed.core.collection_strategies import (
    RESTPollingStrategy,
    WebSocketStrategy,
)
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.exchange_registry import ExchangeRegistry

# Import the adapter factory
from candles_feed.core.hummingbot_network_client_adapter import NetworkClientFactory
from candles_feed.core.network_config import NetworkConfig
from candles_feed.core.protocols import (
    Logger,
)


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
        self.logger = logger or logging.getLogger(__name__)
        self._network_config = network_config

        # Get adapter from registry
        self._adapter = ExchangeRegistry.get_adapter_instance(
            exchange, network_config=network_config
        )
        self.ex_trading_pair = self._adapter.get_trading_pair_format(trading_pair)

        # Initialize components
        self._candles: Deque[CandleData] = deque(maxlen=max_records)

        # Create the appropriate network client based on available components
        self._network_client = NetworkClientFactory.create_client(
            hummingbot_components=hummingbot_components, logger=self.logger
        )
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

        :param strategy: Strategy to use ("auto", "websocket", or "polling")
        """
        if self._active:
            return

        self.logger.debug(f"Starting candles feed for {self.trading_pair} on {self.exchange}")

        # Determine which strategy to use
        use_websocket = False

        if strategy == "auto":
            # Check if the interval is supported by websocket
            ws_intervals = self._adapter.get_ws_supported_intervals()
            use_websocket = self.interval in ws_intervals
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

        # Clean up network client resources
        await self._network_client.close()

        self._active = False

    def get_candles(self) -> list[CandleData]:
        """Get the candles.

        :return: List of candle data objects
        """
        return list(self._candles)

    def add_candle(self, candle: CandleData) -> None:
        """Add a candle to the feed manually.

        This is primarily used for testing.

        :param candle: Candle data to add
        """
        self._candles.append(candle)

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
        """Fetch historical candles.

        :param start_time: Start time for fetching candles (timestamp in seconds)
        :param end_time: End time for fetching candles (timestamp in seconds)
        :param limit: Maximum number of candles to fetch
        :return: List of candle data
        """
        # Use REST polling regardless of current strategy
        strategy = self._rest_strategy or self._create_rest_strategy()

        # Use poll_once which is the actual method implemented in RESTPollingStrategy
        candles = await strategy.poll_once(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        # Add the fetched candles to the store
        for candle in candles:
            self.add_candle(candle)

        return candles

    async def get_historical_candles(self, start_time: int, end_time: int) -> pd.DataFrame:
        """Get historical candles between start and end time.

        This is a compatibility method for the original implementation.

        :param start_time: Start time in seconds
        :param end_time: End time in seconds
        :return: DataFrame with candle data
        """
        candles = await self.fetch_candles(start_time=start_time, end_time=end_time)
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
                for c in candles
                if start_time <= c.timestamp <= end_time
            ]
        )

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

    def _round_timestamp_to_interval_multiple(self, timestamp: int) -> int:
        """Round timestamp to nearest interval boundary.

        :param timestamp: Timestamp in seconds
        :return: Rounded timestamp
        """
        interval_seconds = self._adapter.get_supported_intervals()[self.interval]
        return int(timestamp - timestamp % interval_seconds)

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
            if not np.all(np.isclose(unique_diffs, interval_seconds, rtol=1e-5)):
                self.logger.warning("Candles do not have equal intervals")
                return False

        return True
