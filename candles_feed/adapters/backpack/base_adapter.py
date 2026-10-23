"""
Base Backpack adapter implementation for the Candle Feed framework.

Backpack spot and perpetual markets share the REST endpoint and websocket stream;
only the market symbol differs.
"""

import time
from datetime import UTC, datetime
from typing import Any, override

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.intervals import is_variable_length_interval, shift_boundaries
from candles_feed.core.network_config import NetworkConfig
from candles_feed.core.protocols import NetworkClientProtocol
from candles_feed.core.rate_limiter import RestRateLimit

from .constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)


class BackpackBaseAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Base class for Backpack spot and perpetual adapters.

    Timestamps are sent in seconds; the API returns candle boundaries as
    UTC ISO-8601 strings without a timezone designator.
    """

    TIMESTAMP_UNIT: str = "seconds"
    MAX_CANDLES_PER_REQUEST = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST

    # hummingbot/data_feed/candles_feed/backpack_spot_candles/constants.py:38-39 (same in backpack_perpetual_candles/constants.py:38-39) — 6000 weight/60s, klines weight 1
    # Spot and perpetual share the same host and the same REQUEST_WEIGHT pool, so they share one pool.
    REST_RATE_LIMIT = RestRateLimit(max_requests=6000, period_seconds=60)
    REST_RATE_LIMIT_POOL = "backpack"

    def __init__(self, *args: Any, network_config: NetworkConfig | None = None, **kwargs: Any):
        """Accept the ``network_config`` kwarg CandlesFeed passes (no testnet exists).

        :param network_config: Ignored; Backpack has a single environment
        """
        super().__init__()
        self.network_config = network_config

    @staticmethod
    def _iso_to_seconds(iso_timestamp: str) -> int:
        """Convert a Backpack ISO-8601 UTC string to epoch seconds.

        Backpack omits the timezone designator, so a naive value is always
        interpreted as UTC (never as the host's local time).

        :param iso_timestamp: e.g. "2024-01-01T00:00:00" or "2024-01-01 00:00:00"
        :returns: Epoch seconds
        """
        parsed = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return int(parsed.timestamp())

    @override
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds."""
        return INTERVALS

    @override
    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by the WebSocket API."""
        return WS_INTERVALS

    @override
    def get_ws_url(self) -> str:
        """Get WebSocket URL."""
        return WSS_URL

    @override
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles."""
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    @override
    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for the REST request.

        Backpack requires ``startTime`` (seconds); when absent it is derived from
        ``limit`` (capped at the per-request maximum). The endpoint has no limit parameter.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Number of candles wanted
        :returns: Request parameters
        """
        if start_time is None:
            count = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST if limit is None else limit
            count = max(1, min(count, MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST))
            now = int(time.time())
            step = INTERVALS.get(interval, 60)
            if is_variable_length_interval(interval):
                start_time = shift_boundaries(now, interval, step, -count)
            else:
                start_time = now - count * step
        return {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "startTime": int(start_time),
        }

    @override
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse the REST response; taker volumes are not reported and are 0.0.

        :param data: List of kline dicts
        :returns: Parsed candles (empty buckets with null OHLC are skipped)
        """
        if not isinstance(data, list):
            raise self._bad_response(data)
        return [
            CandleData(
                timestamp_raw=self._iso_to_seconds(row["start"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                quote_asset_volume=float(row["quoteVolume"]),
                n_trades=int(row["trades"]),
                taker_buy_base_volume=0.0,
                taker_buy_quote_volume=0.0,
            )
            for row in data
            if isinstance(row, dict)
            and all(row.get(field) is not None for field in ("open", "high", "low", "close"))
        ]

    @override
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles asynchronously, trimmed to ``limit`` rows.

        The endpoint has no limit parameter, so the response is trimmed to the earliest
        rows when ``start_time`` is given, else to the newest.
        """
        candles = await AsyncOnlyAdapter._fetch_rest_candles(
            adapter_implementation=self,
            trading_pair=trading_pair,
            interval=interval,
            start_time=start_time,
            limit=limit,
            network_client=network_client,
        )
        count = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST if limit is None else limit
        count = max(1, min(count, MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST))
        if len(candles) <= count:
            return candles
        return candles[:count] if start_time is not None else candles[-count:]

    @override
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload."""
        symbol = self.get_trading_pair_format(trading_pair)
        exchange_interval = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return {"method": "SUBSCRIBE", "params": [f"kline.{exchange_interval}.{symbol}"]}

    @override
    def parse_ws_message(self, data: dict[str, Any] | None) -> list[CandleData] | None:
        """Parse a kline websocket message.

        The kline stream carries no quote volume, so it is approximated as
        ``volume * close``; the exact value arrives with the next REST backfill.

        :param data: WebSocket message
        :returns: Candles, or None when the message is not a (non-empty) kline update
        """
        if not isinstance(data, dict):
            return None
        kline = data.get("data")
        if not isinstance(kline, dict) or kline.get("e") != "kline" or kline.get("o") is None:
            return None
        volume = float(kline["v"])
        close = float(kline["c"])
        return [
            CandleData(
                timestamp_raw=self._iso_to_seconds(kline["t"]),
                open=float(kline["o"]),
                high=float(kline["h"]),
                low=float(kline["l"]),
                close=close,
                volume=volume,
                quote_asset_volume=volume * close,
                n_trades=int(kline["n"]),
                taker_buy_base_volume=0.0,
                taker_buy_quote_volume=0.0,
            )
        ]
