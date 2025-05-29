"""
Collection strategies for the Candle Feed framework.

This module provides different strategies for collecting candle data,
including both WebSocket and REST-based approaches.
"""

import asyncio
import logging
import time
from typing import Deque

from candles_feed.adapters.protocols import AdapterProtocol
from candles_feed.core.candle_data import CandleData
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.protocols import (
    CollectionStrategy,
    Logger,
    WSAssistant,
)


class WebSocketStrategy:
    """Implementation for websocket-based candle retrieval."""

    def __init__(
        self,
        network_client: NetworkClient,
        adapter: AdapterProtocol,
        trading_pair: str,
        interval: str,
        data_processor: DataProcessor,
        candles_store: Deque[CandleData],
        logger: Logger | None = None,
    ):
        """Initialize the WebSocketStrategy.

        :param network_client: Network client for API communication
        :param adapter: Exchange adapter
        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param data_processor: Data processor
        :param candles_store: Deque for storing candles
        :param logger: Logger instance
        """
        self.network_client = network_client
        self.adapter = adapter
        self.trading_pair = trading_pair
        self.interval = interval
        self.data_processor = data_processor
        self._candles = candles_store
        self.logger = logger or logging.getLogger(__name__)
        self._ws_assistant: WSAssistant | None = None
        self._listen_task: asyncio.Task | None = None
        self._running = False
        self._ready_event = asyncio.Event()

    async def start(self) -> None:
        """Start listening for websocket updates."""
        if not self._running:
            self._running = True
            self._listen_task = asyncio.create_task(self._listen_for_updates())

    async def stop(self) -> None:
        """Stop listening for websocket updates."""
        self._running = False

        if self._listen_task:
            self._listen_task.cancel()
            self._listen_task = None

        if self._ws_assistant:
            await self._ws_assistant.disconnect()
            self._ws_assistant = None

    async def poll_once(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> list[CandleData]:
        """Fetch candles for a specific time range (one-time poll).

        For WebSocket strategy, this falls back to REST API for historical data.

        :param start_time: Start time in seconds.
        :param end_time: End time in seconds.
        :param limit: Maximum number of candles to return.
        :returns: List of CandleData objects.
        """
        try:
            # Check if adapter implements async or sync method
            if hasattr(self.adapter, "fetch_rest_candles") and callable(
                self.adapter.fetch_rest_candles
            ):
                candles = await self.adapter.fetch_rest_candles(
                    trading_pair=self.trading_pair,
                    interval=self.interval,
                    start_time=start_time,
                    limit=limit,
                    network_client=self.network_client,
                )
            elif hasattr(self.adapter, "fetch_rest_candles_synchronous") and callable(
                self.adapter.fetch_rest_candles_synchronous
            ):
                candles = await asyncio.to_thread(
                    self.adapter.fetch_rest_candles_synchronous,
                    trading_pair=self.trading_pair,
                    interval=self.interval,
                    start_time=start_time,
                    limit=limit,
                )
            else:
                raise NotImplementedError(
                    "Adapter must implement fetch_rest_candles or fetch_rest_candles_synchronous"
                )

            interval_seconds = self.adapter.get_supported_intervals()[self.interval]
            processed_candles = self.data_processor.sanitize_candles(candles, interval_seconds)
            self.logger.debug(
                f"Fetched {len(processed_candles)} candles via REST for {self.trading_pair}"
            )
            return processed_candles

        except Exception as e:
            self.logger.error(f"Error fetching candles via REST: {e}")
            return []

    async def _listen_for_updates(self) -> None:
        """Listen for websocket updates."""
        # If we have no initial data, fetch it via REST API
        if not self._candles:
            await self._initialize_candles()
        else:
            self._ready_event.set()

        while self._running:
            try:
                ws_url = self.adapter.get_ws_url()
                self._ws_assistant = await self.network_client.establish_ws_connection(ws_url)

                # Subscribe to candle updates
                payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)
                await self.network_client.send_ws_message(self._ws_assistant, payload)

                # Process incoming messages
                async for message in self._ws_assistant.iter_messages():
                    if not self._running:
                        break

                    if candles := self.adapter.parse_ws_message(message):
                        interval_seconds = self.adapter.get_supported_intervals()[self.interval]
                        validated_candles = self.data_processor.sanitize_candles(
                            candles, interval_seconds
                        )
                        self._update_candles(validated_candles)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.exception(f"Error in websocket connection: {e}")
                # If we have a connection, try to disconnect
                if self._ws_assistant:
                    try:
                        await self._ws_assistant.disconnect()
                    except Exception:  # Use explicit Exception instead of bare except
                        pass
                    finally:
                        self._ws_assistant = None

                if self._running:
                    await asyncio.sleep(1.0)

    async def _initialize_candles(self) -> None:
        """Initialize candles using REST API."""
        try:
            # Get enough candles to fill the store
            limit = self._candles.maxlen
            candles = await self.poll_once(limit=limit)
            if candles:
                for candle in candles:
                    self._candles.append(candle)
                self._ready_event.set()
            else:
                self.logger.warning("Failed to initialize candles, will retry")
        except Exception as e:
            self.logger.error(f"Error initializing candles: {e}")

    def _update_candles(self, new_candles: list[CandleData]) -> None:
        """Update the candles store with new data.

        :param new_candles: New candles to update.
        """
        if not new_candles:
            return

        # Either update existing candle or append new one
        for candle in new_candles:
            self.data_processor.process_candle(candle, self._candles)


class RESTPollingStrategy:
    """Implementation for REST-based polling candle retrieval."""

    def __init__(
        self,
        network_client: NetworkClient,
        adapter: AdapterProtocol,
        trading_pair: str,
        interval: str,
        data_processor: DataProcessor,
        candles_store: Deque[CandleData],
        logger: Logger | None = None,
    ):
        """Initialize the RESTPollingStrategy.

        :param network_client: Network client for API communication.
        :param adapter: Exchange adapter.
        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :param data_processor: Data processor.
        :param candles_store: Deque for storing candles.
        :param logger: Logger instance.
        """
        self.network_client = network_client
        self.adapter = adapter
        self.trading_pair = trading_pair
        self.interval = interval
        self.data_processor = data_processor
        self._candles = candles_store
        self.logger = logger or logging.getLogger(__name__)
        self._polling_task: asyncio.Task | None = None
        self._polling_interval = adapter.get_supported_intervals()[interval]
        self._running = False
        self._ready_event = asyncio.Event()

    async def start(self) -> None:
        """Start polling for updates."""
        if not self._running:
            self._running = True
            self._polling_task = asyncio.create_task(self._poll_for_updates())

    async def stop(self) -> None:
        """Stop polling for updates."""
        self._running = False
        if self._polling_task:
            self._polling_task.cancel()
            self._polling_task = None

        # Make sure we clean up any remaining network resources
        # The parent CandlesFeed class will close the network client

    async def poll_once(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> list[CandleData]:
        """Fetch candles for a specific time range (one-time poll).

        :param start_time: Start time in seconds.
        :param end_time: End time in seconds.
        :param limit: Maximum number of candles to return.
        :returns: List of CandleData objects.
        """
        # Adjust start/end time to align with intervals
        interval_seconds = self.adapter.get_supported_intervals()[self.interval]

        # Calculate proper parameters
        if end_time is None:
            end_time = int(time.time())

        # Round down to nearest interval
        end_time = end_time - (end_time % interval_seconds)

        if start_time is None and limit is not None:
            start_time = end_time - (limit * interval_seconds)
        elif start_time is not None:
            start_time = start_time - (start_time % interval_seconds)

        candles: list[CandleData] = []
        try:
            # Check if adapter implements async or sync method
            if hasattr(self.adapter, "fetch_rest_candles") and callable(
                self.adapter.fetch_rest_candles
            ):
                candles = await self.adapter.fetch_rest_candles(
                    trading_pair=self.trading_pair,
                    interval=self.interval,
                    start_time=start_time,
                    limit=limit,
                    network_client=self.network_client,
                )
            elif hasattr(self.adapter, "fetch_rest_candles_synchronous") and callable(
                self.adapter.fetch_rest_candles_synchronous
            ):
                candles = await asyncio.to_thread(
                    self.adapter.fetch_rest_candles_synchronous,
                    trading_pair=self.trading_pair,
                    interval=self.interval,
                    start_time=start_time,
                    limit=limit,
                )
            else:
                raise NotImplementedError(
                    "Adapter must implement fetch_rest_candles or fetch_rest_candles_synchronous"
                )
        except Exception as e:
            self.logger.exception(f"Failed fetching candles: {e}")

        return self.data_processor.sanitize_candles(candles, interval_seconds)

    async def _poll_for_updates(self) -> None:
        """Poll for updates at regular intervals."""
        # Initial fetch to populate the store
        if not self._candles:
            initial_candles = await self.poll_once(limit=self._candles.maxlen)
            if initial_candles:
                # Add all candles to the store
                for candle in initial_candles:
                    self._candles.append(candle)
                self._ready_event.set()
        else:
            self._ready_event.set()

        while self._running:
            try:
                # Calculate parameters for incremental updates
                if self._candles:
                    # Get data since the last candle, excluding the last one
                    # which might be incomplete
                    if len(self._candles) > 1:
                        # If we have more than one candle, we can safely slice
                        candles_without_last = list(self._candles)[:-1]
                        last_complete_ts = max(c.timestamp for c in candles_without_last)
                    else:
                        # If we have only one candle, use its timestamp as starting point
                        last_complete_ts = self._candles[0].timestamp

                    # Fetch new or updated candles
                    candles = await self.poll_once(start_time=last_complete_ts)
                    self._update_candles(candles)

                # Sleep until next interval
                sleep_time = max(
                    self._polling_interval / 2, 1
                )  # At least 1s, but prefer half interval
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Error in polling loop: {e}")
                await asyncio.sleep(1.0)

    def _update_candles(self, new_candles: list[CandleData]) -> None:
        """Update the candles store with new data.

        :param new_candles: New candles to update.
        """
        if not new_candles:
            return

        for candle in new_candles:
            self.data_processor.process_candle(candle, self._candles)


class CollectionStrategyFactory:
    """Factory for creating appropriate collection strategies."""

    @staticmethod
    def create_strategy(
        adapter: AdapterProtocol,
        trading_pair: str,
        interval: str,
        network_client: NetworkClient,
        data_processor: DataProcessor,
        candles_store: Deque[CandleData],
        logger: Logger | None = None,
    ) -> CollectionStrategy:
        """Create appropriate strategy based on adapter capabilities.

        :param adapter: Exchange adapter
        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param network_client: Network client
        :param data_processor: Data processor
        :param candles_store: Deque for storing candles
        :param logger: Logger instance
        :returns: Appropriate collection strategy
        """
        try:
            # Check if adapter supports WebSocket for this interval
            supported_ws_intervals = adapter.get_ws_supported_intervals()
            if supported_ws_intervals and interval in supported_ws_intervals:
                return WebSocketStrategy(
                    network_client=network_client,
                    adapter=adapter,
                    trading_pair=trading_pair,
                    interval=interval,
                    data_processor=data_processor,
                    candles_store=candles_store,
                    logger=logger,
                )
        except (NotImplementedError, AttributeError):
            # If WebSocket is not supported or method not implemented, fall back to REST
            pass

        # Default to REST polling
        return RESTPollingStrategy(
            network_client=network_client,
            adapter=adapter,
            trading_pair=trading_pair,
            interval=interval,
            data_processor=data_processor,
            candles_store=candles_store,
            logger=logger,
        )
