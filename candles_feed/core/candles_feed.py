"""
Core candles feed class for the Candle Feed framework.

This module provides the main class for managing candle data feeds.
"""

import logging
from collections import deque
from typing import Deque, Optional

import pandas as pd

from candles_feed.core.candle_data import CandleData
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.exchange_registry import ExchangeRegistry
# Import the adapter factory
from candles_feed.core.hummingbot_network_client_adapter import NetworkClientFactory
from candles_feed.core.collection_strategies import (
    RESTPollingStrategy,
    WebSocketStrategy,
)
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
        hummingbot_components: Optional[dict] = None,
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
        """
        self.exchange = exchange
        self.trading_pair = trading_pair
        self.interval = interval
        self.max_records = max_records
        self.logger = logger or logging.getLogger(__name__)

        # Get adapter from registry
        self._adapter = ExchangeRegistry.get_adapter_instance(exchange)
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
                raise ValueError("WebSocket strategy not supported by this adapter")

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

        :param start_time: Start time in seconds (optional)
        :param end_time: End time in seconds (optional)
        :param limit: Maximum number of candles to fetch (default: 500)
        :return: List of candle data objects
        """
        self.logger.debug(f"Fetching historical candles for {self.trading_pair} on {self.exchange}")

        # Create REST strategy if it doesn't exist
        if not self._rest_strategy:
            self._rest_strategy = self._create_rest_strategy()

        if not self._rest_strategy:
            raise ValueError("REST polling strategy not supported by this adapter")

        # Fetch candles
        candles = await self._rest_strategy.poll_once(start_time, end_time, limit)

        # Add candles to the store
        if candles:
            # Clear existing candles if fetching from the beginning
            if start_time is None or (
                len(self._candles) > 0 and start_time < self._candles[0].timestamp
            ):
                self._candles.clear()

            # Add each candle to the store
            for candle in candles:
                self._data_processor.process_candle(candle, self._candles)

        return candles

    def get_candles(self) -> list[CandleData]:
        """Get raw candle data.

        :return: List of CandleData objects
        """
        return list(self._candles)

    def add_candle(self, candle: CandleData) -> None:
        """Add a candle to the store.

        :param candle: Candle data to add
        """
        self._data_processor.process_candle(candle, self._candles)

    @property
    def ready(self) -> bool:
        """Check if the feed is ready.

        :return: True if the feed is ready, False otherwise
        """
        return len(self._candles) >= self.max_records * 0.9  # At least 90% filled

    @property
    def last_timestamp(self) -> int | None:
        """Get the timestamp of the most recent candle.

        :return: Timestamp in seconds, or None if no candles available
        """
        return self._candles[-1].timestamp if self._candles else None

    @property
    def first_timestamp(self) -> int | None:
        """Get the timestamp of the oldest candle.

        :return: Timestamp in seconds, or None if no candles available
        """
        return self._candles[0].timestamp if self._candles else None
