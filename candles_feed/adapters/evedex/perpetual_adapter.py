"""
Evedex perpetual exchange adapter for the Candle Feed framework.

REST only: Evedex streams candles over a Centrifugo websocket that needs a
connect handshake and ping/pong replies, which the framework's single-payload
websocket model cannot express. The framework falls back to REST polling.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Any, override

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter, NoWebSocketSupportMixin
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.intervals import is_variable_length_interval, shift_boundaries
from candles_feed.core.network_config import NetworkConfig
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    CANDLES_ENDPOINT,
    EXCHANGE_REST_URL,
    INSTRUMENTS_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MARKET_DATA_REST_URL,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    NANOSECOND_TIMESTAMP_THRESHOLD,
)

_WRAPPER_KEYS = ("data", "result", "candles")


def _pick(row: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    """First value present (not None) under ``keys``, else ``default``."""
    for key in keys:
        if row.get(key) is not None:
            return row[key]
    return default


@ExchangeRegistry.register("evedex_perpetual")
class EvedexPerpetualAdapter(NoWebSocketSupportMixin, BaseAdapter, AsyncOnlyAdapter):
    """Evedex perpetual exchange adapter.

    Trading pair format: "BTC-USDT" -> derived "BTCUSD" (USDT quoted as USD); the exact
    instrument name is looked up from the exchange once per pair when fetching.
    """

    TIMESTAMP_UNIT: str = "milliseconds"
    MAX_CANDLES_PER_REQUEST = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST

    def __init__(self, *args: Any, network_config: NetworkConfig | None = None, **kwargs: Any):
        """Accept the ``network_config`` kwarg CandlesFeed passes (no testnet exists)."""
        super().__init__()
        self.network_config = network_config
        self._instrument_names: dict[str, str] = {}
        self._logger = logging.getLogger(__name__)

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Derive the instrument name: "BTC-USDT" -> "BTCUSD"."""
        base, quote = trading_pair.split("-", 1)
        return f"{base}{'USD' if quote == 'USDT' else quote}"

    @override
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds."""
        return INTERVALS

    @override
    def _get_rest_url(self) -> str:
        """Get the candles URL template (the instrument is substituted per pair)."""
        return f"{MARKET_DATA_REST_URL}{CANDLES_ENDPOINT}"

    def _get_rest_url_for_pair(self, trading_pair: str) -> str:
        """Candles URL for ``trading_pair`` using its resolved (or derived) instrument."""
        instrument = self._instrument_names.get(
            trading_pair, self.get_trading_pair_format(trading_pair)
        )
        return self._get_rest_url().format(instrument=instrument)

    @staticmethod
    def _to_iso(timestamp_s: int) -> str:
        """Seconds -> "YYYY-MM-DDTHH:MM:SS.mmmZ"."""
        moment = datetime.fromtimestamp(timestamp_s, tz=UTC)
        return moment.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    @override
    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str]:
        """Get parameters: ``group`` plus ISO-8601 ``after``/``before`` window bounds.

        The window is ``[start, start + limit * interval]``; without ``start_time``
        it ends now.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Number of candles wanted (capped at the per-request maximum)
        :returns: Request parameters
        """
        count = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST if limit is None else limit
        count = max(1, min(count, MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST))
        step = INTERVALS.get(interval, 60)
        calendar = is_variable_length_interval(interval)
        if start_time is None:
            end_s = int(time.time())
            start_s = (
                shift_boundaries(end_s, interval, step, -count)
                if calendar
                else end_s - count * step
            )
        else:
            start_s = int(start_time)
            end_s = (
                shift_boundaries(start_s, interval, step, count)
                if calendar
                else start_s + count * step
            )
        return {
            "group": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "after": self._to_iso(start_s),
            "before": self._to_iso(end_s),
        }

    def _timestamp_seconds(self, raw: Any) -> int:
        """Convert a raw timestamp (s, ms, ns or ISO string) to seconds."""
        if not isinstance(raw, str) and float(raw) >= NANOSECOND_TIMESTAMP_THRESHOLD:
            return int(float(raw) / 1e9)
        return self.ensure_timestamp_in_seconds(raw)

    def _row_to_candle(self, row: Any, interval_seconds: int | None) -> CandleData | None:
        """Parse a list row ``[ts, open, close, high, low, (volume_usd,) volume]`` or a dict."""
        if isinstance(row, list):
            if len(row) < 6:
                return None
            ts, open_, close, high, low = row[:5]
            volume_usd, volume = (row[5], row[6]) if len(row) >= 7 else (0.0, row[5])
        elif isinstance(row, dict):
            ts = _pick(row, ("timestamp", "t", "time"))
            open_, close = _pick(row, ("open", "o")), _pick(row, ("close", "c"))
            high, low = _pick(row, ("high", "h")), _pick(row, ("low", "l"))
            volume = _pick(row, ("volume", "v"), 0.0)
            volume_usd = _pick(row, ("volumeUsd", "quoteVolume", "q"), 0.0)
        else:
            return None
        if any(v is None for v in (ts, open_, close, high, low)):
            return None
        try:
            seconds = self._timestamp_seconds(ts)
        except ValueError:
            return None
        # Weekly/monthly buckets are not epoch-aligned (Monday / month start): keep as returned
        if interval_seconds and interval_seconds < INTERVALS["1w"]:
            seconds -= seconds % interval_seconds
        return CandleData(
            timestamp_raw=seconds,
            open=float(open_),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=float(volume),
            quote_asset_volume=float(volume_usd),
            n_trades=0,
            taker_buy_base_volume=0.0,
            taker_buy_quote_volume=0.0,
        )

    @override
    def _parse_rest_response(
        self, data: dict | list | None, interval_seconds: int | None = None
    ) -> list[CandleData]:
        """Parse the REST response into candles sorted ascending.

        :param data: A list of rows, or a dict wrapping them under data/result/candles
        :param interval_seconds: When given (and below one week), timestamps are floored to
            the interval multiple and rows landing in the same bucket collapse to the latest one
        :returns: Parsed candles
        """
        rows = _pick(data, _WRAPPER_KEYS) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise self._bad_response(data)
        by_timestamp: dict[int, CandleData] = {}
        for row in rows:
            candle = self._row_to_candle(row, interval_seconds)
            if candle is not None:
                by_timestamp[candle.timestamp] = candle
        return [by_timestamp[ts] for ts in sorted(by_timestamp)]

    async def _resolve_instrument(
        self, trading_pair: str, network_client: NetworkClientProtocol
    ) -> None:
        """Resolve and cache the instrument name; failures fall back to the derived name."""
        if trading_pair in self._instrument_names:
            return
        base, quote = trading_pair.split("-", 1)
        try:
            instruments = await network_client.get_rest_data(
                url=f"{EXCHANGE_REST_URL}{INSTRUMENTS_ENDPOINT}"
            )
        except Exception as e:
            self._logger.warning(f"Could not resolve Evedex instrument for {trading_pair}: {e}")
            return
        rows = instruments.get("list", []) if isinstance(instruments, dict) else instruments
        for instrument in rows if isinstance(rows, list) else []:
            if not isinstance(instrument, dict):
                continue
            inst_base = (instrument.get("from") or {}).get("symbol")
            inst_quote = (instrument.get("to") or {}).get("symbol")
            quote_matches = inst_quote == quote or (quote == "USDT" and inst_quote == "USD")
            if inst_base == base and quote_matches:
                if instrument.get("name"):
                    self._instrument_names[trading_pair] = str(instrument["name"])
                return

    @override
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles, resolving the instrument name first (once per pair)."""
        if network_client is None:
            raise ValueError("network_client is required for async operations")
        await self._resolve_instrument(trading_pair, network_client)
        response = await network_client.get_rest_data(
            url=self._get_rest_url_for_pair(trading_pair),
            params=self._get_rest_params(trading_pair, interval, start_time, limit),
        )
        return self._parse_rest_response(response, interval_seconds=INTERVALS.get(interval))
