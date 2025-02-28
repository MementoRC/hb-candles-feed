"""
Network strategies for the Candle Feed framework.

This module provides different network strategies for fetching candle data,
including both WebSocket and REST-based approaches.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Deque, Dict, List, Optional, Type

from candles_feed.core.candle_data import CandleData
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.protocols import CandleDataAdapter, Logger, NetworkStrategy, WSAssistant


class WebSocketStrategy:
    """Implementation for websocket-based candle retrieval."""

    def __init__(self,
                 network_client: NetworkClient,
                 adapter: CandleDataAdapter,
                 trading_pair: str,
                 interval: str,
                 data_processor: DataProcessor,
                 candles_store: Deque[CandleData],
                 logger: Optional[Logger] = None):
        """Initialize the WebSocketStrategy.

        Args:
            network_client: Network client for API communication
            adapter: Exchange adapter
            trading_pair: Trading pair
            interval: Candle interval
            data_processor: Data processor
            candles_store: Deque for storing candles
            logger: Logger instance
        """
        self.network_client = network_client
        self.adapter = adapter
        self.trading_pair = trading_pair
        self.interval = interval
        self.data_processor = data_processor
        self._candles = candles_store
        self.logger = logger or logging.getLogger(__name__)
        self._ws_assistant: Optional[WSAssistant] = None
        self._listen_task: Optional[asyncio.Task] = None
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

    async def poll_once(self,
                      start_time: Optional[int] = None,
                      end_time: Optional[int] = None,
                      limit: Optional[int] = None) -> List[CandleData]:
        """
        Fetch candles for a specific time range (one-time poll).

        For WebSocket strategy, this falls back to REST API for historical data.

        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            limit: Maximum number of candles to return

        Returns:
            List of CandleData objects
        """
        # For historical data, we need to use REST API
        url = self.adapter.get_rest_url()
        params = self.adapter.get_rest_params(
            trading_pair=self.trading_pair,
            interval=self.interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        try:
            response = await self.network_client.get_rest_data(
                url=url,
                params=params
            )

            candles = self.adapter.parse_rest_response(response)
            interval_seconds = self.adapter.get_supported_intervals()[self.interval]

            processed_candles = self.data_processor.sanitize_candles(
                candles,
                interval_seconds
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
                payload = self.adapter.get_ws_subscription_payload(
                    self.trading_pair,
                    self.interval
                )
                await self.network_client.send_ws_message(self._ws_assistant, payload)

                # Process incoming messages
                async for message in self._ws_assistant.iter_messages():
                    if not self._running:
                        break

                    candles = self.adapter.parse_ws_message(message)
                    if candles:
                        interval_seconds = self.adapter.get_supported_intervals()[self.interval]
                        validated_candles = self.data_processor.sanitize_candles(
                            candles,
                            interval_seconds
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

    def _update_candles(self, new_candles: List[CandleData]) -> None:
        """Update the candles store with new data.

        Args:
            new_candles: New candles to update
        """
        if not new_candles:
            return

        # Either update existing candle or append new one
        for candle in new_candles:
            self.data_processor.process_candle(candle, self._candles)


class RESTPollingStrategy:
    """Implementation for REST-based polling candle retrieval."""

    def __init__(self,
                 network_client: NetworkClient,
                 adapter: CandleDataAdapter,
                 trading_pair: str,
                 interval: str,
                 data_processor: DataProcessor,
                 candles_store: Deque[CandleData],
                 logger: Optional[Logger] = None):
        """Initialize the RESTPollingStrategy.

        Args:
            network_client: Network client for API communication
            adapter: Exchange adapter
            trading_pair: Trading pair
            interval: Candle interval
            data_processor: Data processor
            candles_store: Deque for storing candles
            logger: Logger instance
        """
        self.network_client = network_client
        self.adapter = adapter
        self.trading_pair = trading_pair
        self.interval = interval
        self.data_processor = data_processor
        self._candles = candles_store
        self.logger = logger or logging.getLogger(__name__)
        self._polling_task: Optional[asyncio.Task] = None
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

    async def poll_once(self,
                       start_time: Optional[int] = None,
                       end_time: Optional[int] = None,
                       limit: Optional[int] = None) -> List[CandleData]:
        """Fetch candles for a specific time range (one-time poll).

        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            limit: Maximum number of candles to return

        Returns:
            List of CandleData objects
        """
        try:
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

            # Get REST parameters from adapter
            params = self.adapter.get_rest_params(
                trading_pair=self.trading_pair,
                interval=self.interval,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )

            # Execute request
            url = self.adapter.get_rest_url()
            response = await self.network_client.get_rest_data(
                url=url,
                params=params
            )

            # Parse and process response
            candles = self.adapter.parse_rest_response(response)
            return self.data_processor.sanitize_candles(candles, interval_seconds)

        except Exception as e:
            self.logger.exception(f"Error fetching candles: {e}")
            return []

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
                    last_complete_ts = max(c.timestamp for c in self._candles[:-1]) \
                                      if len(self._candles) > 1 else None

                    # Fetch new or updated candles
                    candles = await self.poll_once(start_time=last_complete_ts)
                    self._update_candles(candles)

                # Sleep until next interval
                sleep_time = max(self._polling_interval / 2, 1)  # At least 1s, but prefer half interval
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.exception(f"Error in polling loop: {e}")
                await asyncio.sleep(1.0)

    def _update_candles(self, new_candles: List[CandleData]) -> None:
        """Update the candles store with new data.

        Args:
            new_candles: New candles to update
        """
        if not new_candles:
            return

        for candle in new_candles:
            self.data_processor.process_candle(candle, self._candles)


class NetworkStrategyFactory:
    """Factory for creating appropriate network strategies."""

    @staticmethod
    def create_strategy(
        adapter: CandleDataAdapter,
        trading_pair: str,
        interval: str,
        network_client: NetworkClient,
        data_processor: DataProcessor,
        candles_store: Deque[CandleData],
        logger: Optional[Logger] = None
    ) -> NetworkStrategy:
        """Create appropriate strategy based on adapter capabilities.

        Args:
            adapter: Exchange adapter
            trading_pair: Trading pair
            interval: Candle interval
            network_client: Network client
            data_processor: Data processor
            candles_store: Deque for storing candles
            logger: Logger instance

        Returns:
            Appropriate network strategy
        """

        # Check if adapter supports WebSocket for this interval
        if interval in adapter.get_ws_supported_intervals():
            return WebSocketStrategy(
                network_client=network_client,
                adapter=adapter,
                trading_pair=trading_pair,
                interval=interval,
                data_processor=data_processor,
                candles_store=candles_store,
                logger=logger
            )
        else:
            return RESTPollingStrategy(
                network_client=network_client,
                adapter=adapter,
                trading_pair=trading_pair,
                interval=interval,
                data_processor=data_processor,
                candles_store=candles_store,
                logger=logger
            )
