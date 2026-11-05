"""
Base Lighter adapter implementation for the Candle Feed framework.

Lighter spot and perpetual markets share the candles endpoint; they differ in
the symbol format and in which ``orderBookDetails`` list holds the market id.

REST only: Lighter has no websocket candle stream, so the framework polls.
"""

import time
from abc import abstractmethod
from typing import Any, override

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter, NoWebSocketSupportMixin
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.intervals import next_boundary
from candles_feed.core.network_config import NetworkConfig
from candles_feed.core.protocols import NetworkClientProtocol
from candles_feed.core.rate_limiter import RestRateLimit

from .constants import (
    CANDLES_PATH_URL,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAINNET_BASE_URL,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ORDER_BOOK_DETAILS_PATH_URL,
)

_REQUIRED_FIELDS = ("t", "o", "h", "l", "c")


class LighterBaseAdapter(NoWebSocketSupportMixin, BaseAdapter, AsyncOnlyAdapter):
    """Base class for Lighter spot and perpetual adapters. Timestamps are milliseconds."""

    TIMESTAMP_UNIT: str = "milliseconds"
    MAX_CANDLES_PER_REQUEST = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST

    # hummingbot/data_feed/candles_feed/lighter_spot_candles/constants.py:34-36,39,44 (same in lighter_perpetual_candles/constants.py:29-31,34,39) — standard account 60 req/min (18000 pool / weight 300)
    # Spot and perpetual share the same host and the same per-account cap, so they share one pool.
    REST_RATE_LIMIT = RestRateLimit(max_requests=60, period_seconds=60)
    REST_RATE_LIMIT_POOL = "lighter"

    # Key of the orderBookDetails response list that holds this market type
    MARKETS_KEY: str

    def __init__(self, *args: Any, network_config: NetworkConfig | None = None, **kwargs: Any):
        """Accept the ``network_config`` kwarg CandlesFeed passes (no testnet exists)."""
        super().__init__()
        self.network_config = network_config
        self._market_ids: dict[str, int] = {}

    @staticmethod
    @abstractmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert a standard trading pair to the Lighter market symbol."""

    @override
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds."""
        return INTERVALS

    @override
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles."""
        return f"{MAINNET_BASE_URL}{CANDLES_PATH_URL}"

    @staticmethod
    def _window_ms(interval: str, start_time: int | None, limit: int | None) -> tuple[int, int]:
        """Compute the ``(start, end)`` request window in milliseconds.

        ``limit`` None means the maximum; zero or negative means one candle (a zero limit
        would otherwise collapse the window to start == end, which Lighter rejects).
        The window ends no later than the end of the current bucket. Without
        ``start_time`` it covers the latest ``limit`` buckets.
        """
        interval_s = INTERVALS[interval]
        count = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST if limit is None else limit
        count = max(1, min(count, MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST))
        now = int(time.time())
        bucket_end = next_boundary(now, interval, interval_s)
        if start_time is None:
            end_s = bucket_end
            start_s = end_s - count * interval_s
        else:
            start_s = int(start_time)
            end_s = min(start_s + count * interval_s, bucket_end)
        return start_s * 1000, end_s * 1000

    @override
    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for the REST request (needs the market id resolved first).

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Number of candles wanted
        :returns: Request parameters
        :raises ValueError: If the market id is unresolved, or the window is empty
            (end_timestamp not greater than start_timestamp)
        """
        if trading_pair not in self._market_ids:
            raise ValueError(f"Lighter market id not resolved for {trading_pair}")
        start_ms, end_ms = self._window_ms(interval, start_time, limit)
        if end_ms <= start_ms:
            raise ValueError(
                f"Invalid candle time range for {trading_pair}: end_timestamp ({end_ms}) "
                f"must be greater than start_timestamp ({start_ms})."
            )
        return {
            "market_id": self._market_ids[trading_pair],
            "resolution": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "start_timestamp": start_ms,
            "end_timestamp": end_ms,
            "count_back": max(1, (end_ms - start_ms) // (INTERVALS[interval] * 1000)),
        }

    @override
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse ``{"c": [...]}`` into candles sorted ascending; taker volumes are 0.0.

        Rows lacking a timestamp or any price are dropped (never zero-filled).
        """
        rows = data.get("c") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise self._bad_response(data)
        candles = [
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(row["t"]),
                open=float(row["o"]),
                high=float(row["h"]),
                low=float(row["l"]),
                close=float(row["c"]),
                volume=float(row.get("v") or 0.0),
                quote_asset_volume=float(row.get("V") or 0.0),
                n_trades=0,
                taker_buy_base_volume=0.0,
                taker_buy_quote_volume=0.0,
            )
            for row in rows
            if isinstance(row, dict) and all(row.get(k) is not None for k in _REQUIRED_FIELDS)
        ]
        return sorted(candles, key=lambda c: c.timestamp)

    async def _resolve_market_id(
        self, trading_pair: str, network_client: NetworkClientProtocol
    ) -> None:
        """Look up and cache the market id from ``orderBookDetails``.

        :raises ValueError: If the market is not listed
        """
        if trading_pair in self._market_ids:
            return
        symbol = self.get_trading_pair_format(trading_pair).upper()
        details = await network_client.get_rest_data(
            url=f"{MAINNET_BASE_URL}{ORDER_BOOK_DETAILS_PATH_URL}"
        )
        markets = details.get(self.MARKETS_KEY, []) if isinstance(details, dict) else []
        for market in markets:
            if str(market.get("symbol", "")).upper() == symbol:
                self._market_ids[trading_pair] = int(market["market_id"])
                return
        raise ValueError(f"Lighter market not found for trading pair {trading_pair}")

    @override
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles; an empty window (nothing to fetch yet) returns ``[]`` without a request."""
        if network_client is None:
            raise ValueError("network_client is required for async operations")
        start_ms, end_ms = self._window_ms(interval, start_time, limit)
        if end_ms <= start_ms:
            return []
        await self._resolve_market_id(trading_pair, network_client)
        response = await network_client.get_rest_data(
            url=self._get_rest_url(),
            params=self._get_rest_params(trading_pair, interval, start_time, limit),
        )
        return self._parse_rest_response(response)
