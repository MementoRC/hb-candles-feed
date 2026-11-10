"""
Collection strategies for the Candle Feed framework.

This module provides different strategies for collecting candle data,
including both WebSocket and REST-based approaches.
"""

import asyncio
import inspect
import logging
import random
import time
from collections import deque

from candles_feed.adapters.protocols import AdapterProtocol
from candles_feed.core.candle_data import CandleData
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.intervals import floor_timestamp, shift_boundaries
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.protocols import (
    CollectionStrategy,
    Logger,
    WSAssistant,
)
from candles_feed.core.rate_limiter import resolve_adapter_rate_limiter, run_paced


class WebSocketStrategy:
    """Implementation for websocket-based candle retrieval."""

    RECONNECT_BASE_DELAY = 1.0
    RECONNECT_MAX_DELAY = 30.0
    MIN_INACTIVITY_TIMEOUT = 60
    MAX_INACTIVITY_TIMEOUT = 600

    def __init__(
        self,
        network_client: NetworkClient,
        adapter: AdapterProtocol,
        trading_pair: str,
        interval: str,
        data_processor: DataProcessor,
        candles_store: deque[CandleData],
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
        self._reconnect_attempts = 0

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
        end_time: int | None = None,  # end_time is not used by fetch_rest_candles
        limit: int | None = None,
    ) -> list[CandleData]:
        """Fetch candles for a specific time range (one-time poll).

        For WebSocket strategy, this falls back to REST API for historical data.

        :param start_time: Start time in seconds.
        :param end_time: End time in seconds (currently not utilized by underlying calls).
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
                candles = await run_paced(
                    resolve_adapter_rate_limiter(self.adapter),
                    lambda: asyncio.to_thread(
                        self.adapter.fetch_rest_candles_synchronous,
                        trading_pair=self.trading_pair,
                        interval=self.interval,
                        start_time=start_time,
                        limit=limit,
                    ),
                )
            else:
                raise NotImplementedError(
                    "Adapter must implement fetch_rest_candles or fetch_rest_candles_synchronous"
                )

            interval_seconds = self.adapter.get_supported_intervals()[self.interval]
            processed_candles = self.data_processor.sanitize_candles(
                candles, interval_seconds, self.interval
            )
            self.logger.debug(
                f"Fetched {len(processed_candles)} candles via REST for {self.trading_pair}"
            )
            return processed_candles

        except Exception as e:
            self.logger.error(f"Error fetching candles via REST: {e}")
            return []

    def _next_reconnect_delay(self) -> float:
        """Return the jittered exponential backoff delay for the next reconnect attempt.

        :returns: Delay in seconds, between half and all of the capped exponential step.
        """
        step = self.RECONNECT_BASE_DELAY * 2 ** min(self._reconnect_attempts, 16)
        self._reconnect_attempts += 1
        # Jitter spreads reconnects of many feeds; it is not security-sensitive
        return min(step, self.RECONNECT_MAX_DELAY) * random.uniform(0.5, 1.0)  # noqa: S311

    def _ws_inactivity_timeout(self) -> float | None:
        """Return how long the receive loop may stay silent before forcing a reconnect.

        Adapters may override this with an optional ``get_ws_inactivity_timeout()`` hook
        (e.g. a few times the server ping interval); returning None disables the watchdog.

        :returns: Timeout in seconds, or None for no watchdog.
        """
        hook = getattr(self.adapter, "get_ws_inactivity_timeout", None)
        if callable(hook):
            return hook()
        interval_seconds = self.adapter.get_supported_intervals()[self.interval]
        return float(
            min(max(2 * interval_seconds, self.MIN_INACTIVITY_TIMEOUT), self.MAX_INACTIVITY_TIMEOUT)
        )

    async def _listen_for_updates(self) -> None:
        """Listen for websocket updates, reconnecting with backoff when the connection drops."""
        # If we have no initial data, fetch it via REST API
        if not self._candles:
            await self._initialize_candles()
        else:
            self._ready_event.set()

        while self._running:
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                self.logger.warning(
                    f"No websocket message for {self.trading_pair} within the inactivity timeout"
                )
            except Exception as e:
                self.logger.exception(f"Error in websocket connection: {e}")

            await self._disconnect_ws()
            if self._running:
                delay = self._next_reconnect_delay()
                self.logger.info(f"Reconnecting websocket for {self.trading_pair} in {delay:.1f}s")
                await asyncio.sleep(delay)

    async def _connect_and_listen(self) -> None:
        """Run one websocket session: connect, subscribe, catch up via REST, process messages.

        Returns when the server closes the stream; raises TimeoutError when it goes silent.
        """
        ws_url = self.adapter.get_ws_url()
        self._ws_assistant = await self.network_client.establish_ws_connection(ws_url)

        # Optional adapter hooks (not part of BaseAdapter's API):
        #   get_ws_connect_payload() -> dict | None: handshake sent once per
        #       (re)connection, before the subscription.
        #   get_ws_reply(message) -> dict | None: reply (e.g. pong) sent back for a
        #       server message instead of parsing it as candles; {} is a valid reply.
        connect_hook = getattr(self.adapter, "get_ws_connect_payload", None)
        if callable(connect_hook) and (connect_payload := connect_hook()) is not None:
            await self.network_client.send_ws_message(self._ws_assistant, connect_payload)

        # Let adapters that need exchange metadata resolve it before subscribing
        prepare = getattr(self.adapter, "prepare_ws_subscription", None)
        if callable(prepare) and inspect.isawaitable(
            pending := prepare(self.trading_pair, self.network_client)
        ):
            await pending

        # Subscribe to candle updates
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)
        await self.network_client.send_ws_message(self._ws_assistant, payload)

        # Candles published before the subscription became active (startup snapshot, or the
        # time spent disconnected) never arrive over the websocket, so fill them via REST
        if self._candles:
            await self._catch_up_candles()
        else:
            await self._initialize_candles()

        # Process incoming messages
        timeout = self._ws_inactivity_timeout()
        messages = aiter(self._ws_assistant.iter_messages())
        while self._running:
            try:
                async with asyncio.timeout(timeout):
                    message = await anext(messages)
            except StopAsyncIteration:
                return

            # The server is delivering again, so the next drop starts a fresh backoff
            self._reconnect_attempts = 0

            reply_hook = getattr(self.adapter, "get_ws_reply", None)
            if callable(reply_hook) and (reply := reply_hook(message)) is not None:
                await self.network_client.send_ws_message(self._ws_assistant, reply)
                continue

            if candles := self.adapter.parse_ws_message(message):
                interval_seconds = self.adapter.get_supported_intervals()[self.interval]
                validated_candles = self.data_processor.sanitize_candles(
                    candles, interval_seconds, self.interval
                )
                self._update_candles(validated_candles)

    async def _disconnect_ws(self) -> None:
        """Disconnect the current websocket, if any, ignoring errors from a dead connection."""
        if self._ws_assistant:
            try:
                await self._ws_assistant.disconnect()
            except Exception:  # Use explicit Exception instead of bare except
                pass
            finally:
                self._ws_assistant = None

    async def _catch_up_candles(self) -> None:
        """Fetch candles from the latest stored timestamp onward via REST and merge them."""
        since = self._candles[-1].timestamp
        candles = await self.poll_once(start_time=since, limit=self._candles.maxlen)
        self._update_candles(candles)
        self._ready_event.set()
        if candles:
            self.logger.debug(
                f"Caught up {len(candles)} candles since {since} for {self.trading_pair}"
            )

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
        candles_store: deque[CandleData],
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

    async def fetch_rest_page(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> list[CandleData]:
        """Fetch one raw page of candles without sanitizing or swallowing errors.

        :param start_time: Start time in seconds.
        :param end_time: End time in seconds (used to derive start_time when only limit is given).
        :param limit: Maximum number of candles to return.
        :returns: List of CandleData objects exactly as the adapter returned them.
        :raises NotImplementedError: If the adapter has no REST fetch method.
        """
        # Adjust start/end time to align with intervals
        interval_seconds = self.adapter.get_supported_intervals()[self.interval]

        # Calculate proper parameters
        if end_time is None:
            end_time = int(time.time())

        # Round down to nearest interval
        end_time = floor_timestamp(end_time, self.interval, interval_seconds)

        if start_time is None and limit is not None:
            start_time = shift_boundaries(end_time, self.interval, interval_seconds, -limit)
        elif start_time is not None:
            start_time = floor_timestamp(start_time, self.interval, interval_seconds)

        # Check if adapter implements async or sync method
        if hasattr(self.adapter, "fetch_rest_candles") and callable(
            self.adapter.fetch_rest_candles
        ):
            return await self.adapter.fetch_rest_candles(
                trading_pair=self.trading_pair,
                interval=self.interval,
                start_time=start_time,
                limit=limit,
                network_client=self.network_client,
            )
        if hasattr(self.adapter, "fetch_rest_candles_synchronous") and callable(
            self.adapter.fetch_rest_candles_synchronous
        ):
            return await run_paced(
                resolve_adapter_rate_limiter(self.adapter),
                lambda: asyncio.to_thread(
                    self.adapter.fetch_rest_candles_synchronous,
                    trading_pair=self.trading_pair,
                    interval=self.interval,
                    start_time=start_time,
                    limit=limit,
                ),
            )
        raise NotImplementedError(
            "Adapter must implement fetch_rest_candles or fetch_rest_candles_synchronous"
        )

    async def poll_once(
        self,
        start_time: int | None = None,
        end_time: int
        | None = None,  # end_time is used here for calculation, but not directly by fetch_rest_candles
        limit: int | None = None,
    ) -> list[CandleData]:
        """Fetch candles for a specific time range (one-time poll).

        :param start_time: Start time in seconds.
        :param end_time: End time in seconds.
        :param limit: Maximum number of candles to return.
        :returns: List of CandleData objects.
        """
        interval_seconds = self.adapter.get_supported_intervals()[self.interval]

        candles: list[CandleData] = []
        try:
            candles = await self.fetch_rest_page(
                start_time=start_time, end_time=end_time, limit=limit
            )
        except Exception as e:
            self.logger.exception(f"Failed fetching candles: {e}")

        return self.data_processor.sanitize_candles(candles, interval_seconds, self.interval)

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
                else:
                    # Initial fetch failed or returned nothing: retry the full fetch
                    initial_candles = await self.poll_once(limit=self._candles.maxlen)
                    if initial_candles:
                        for candle in initial_candles:
                            self._candles.append(candle)
                        self._ready_event.set()

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
        candles_store: deque[CandleData],
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
