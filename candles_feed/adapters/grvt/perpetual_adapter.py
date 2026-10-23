"""
GRVT perpetual exchange adapter for the Candle Feed framework.

The kline endpoint is a JSON POST, so ``fetch_rest_candles`` is overridden to send
the request body instead of query parameters.
"""

import itertools
import time
from typing import Any, override

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_config import EndpointType, NetworkConfig
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    CANDLE_TYPE,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    KLINE_PATH_URL,
    MAINNET_REST_URL,
    MAINNET_WSS_URL,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    NANOSECONDS_PER_SECOND,
    PUBLIC_WS_CHANNEL_CANDLE,
    TESTNET_REST_URL,
    TESTNET_WSS_URL,
    WS_INTERVALS,
)

_REQUIRED_FIELDS = ("open_time", "open", "high", "low", "close", "volume_b", "volume_q", "trades")


@ExchangeRegistry.register("grvt_perpetual")
class GrvtPerpetualAdapter(BaseAdapter, AsyncOnlyAdapter):
    """GRVT perpetual exchange adapter.

    Trading pair format: "BTC-USDT" -> "BTC_USDT_Perp". Request timestamps are
    nanosecond strings; ``open_time`` in responses is nanoseconds.
    """

    # Seconds are the framework-facing unit; nanosecond strings are built explicitly.
    TIMESTAMP_UNIT: str = "seconds"
    MAX_CANDLES_PER_REQUEST = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST

    def __init__(self, *args: Any, network_config: NetworkConfig | None = None, **kwargs: Any):
        """Initialize the adapter.

        :param network_config: A testnet CANDLES environment selects the testnet hosts
        """
        super().__init__()
        self.network_config = network_config
        self._ws_request_ids = itertools.count(1)

    @property
    def _is_testnet(self) -> bool:
        return self.network_config is not None and self.network_config.is_testnet_for(
            EndpointType.CANDLES
        )

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert "BTC-USDT" to GRVT's "BTC_USDT_Perp"."""
        return trading_pair.replace("-", "_") + "_Perp"

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
        return TESTNET_WSS_URL if self._is_testnet else MAINNET_WSS_URL

    @override
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles."""
        base = TESTNET_REST_URL if self._is_testnet else MAINNET_REST_URL
        return f"{base}/{KLINE_PATH_URL}"

    @override
    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Build the JSON request body.

        The window is ``[start, start + limit * interval]``; because both bounds are
        inclusive it can span ``limit + 1`` buckets, so ``limit + 1`` is requested
        (capped at the per-request maximum). Without ``start_time`` the window ends now.
        Nanosecond values use integer arithmetic: float math would lose precision.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Number of candles wanted
        :returns: Request body
        """
        count = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST if limit is None else limit
        count = max(1, min(count, MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST))
        span = count * INTERVALS.get(interval, 60)
        if start_time is None:
            end_s = int(time.time())
            start_s = end_s - span
        else:
            start_s = int(start_time)
            end_s = start_s + span
        return {
            "instrument": self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "type": CANDLE_TYPE,
            "start_time": str(start_s * NANOSECONDS_PER_SECOND),
            "end_time": str(end_s * NANOSECONDS_PER_SECOND),
            "limit": min(count + 1, MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST),
        }

    @staticmethod
    def _to_candle(row: Any) -> CandleData | None:
        """Parse one candle dict (REST row or WS feed); rows missing a field are dropped."""
        if not isinstance(row, dict) or any(row.get(k) is None for k in _REQUIRED_FIELDS):
            return None
        return CandleData(
            timestamp_raw=BaseAdapter.ensure_timestamp_in_seconds(int(row["open_time"])),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume_b"]),
            quote_asset_volume=float(row["volume_q"]),
            n_trades=int(row["trades"]),
            taker_buy_base_volume=0.0,
            taker_buy_quote_volume=0.0,
        )

    @override
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse ``{"result": [...]}`` into candles sorted ascending by open time."""
        rows = data.get("result") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            return []
        candles = [c for c in map(self._to_candle, rows) if c is not None]
        return sorted(candles, key=lambda c: c.timestamp)

    @override
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles with a JSON POST, trimmed back to ``limit`` rows.

        The ``limit + 1`` boundary request is trimmed to the earliest rows when
        ``start_time`` is given, else to the newest.
        """
        if network_client is None:
            raise ValueError("network_client is required for async operations")
        response = await network_client.get_rest_data(
            url=self._get_rest_url(),
            data=self._get_rest_params(trading_pair, interval, start_time, limit),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        candles = self._parse_rest_response(response)
        count = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST if limit is None else limit
        count = max(1, min(count, MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST))
        if len(candles) <= count:
            return candles
        return candles[:count] if start_time is not None else candles[-count:]

    @override
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get the JSON-RPC subscription payload (request ids increment per call)."""
        code = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        instrument = self.get_trading_pair_format(trading_pair)
        return {
            "jsonrpc": "2.0",
            "method": "subscribe",
            "params": {
                "stream": PUBLIC_WS_CHANNEL_CANDLE,
                "selectors": [f"{instrument}@{code}-{CANDLE_TYPE}"],
            },
            "id": next(self._ws_request_ids),
        }

    @override
    def parse_ws_message(self, data: dict[str, Any] | None) -> list[CandleData] | None:
        """Parse a ``v1.candle`` feed message; other messages return None."""
        if not isinstance(data, dict) or data.get("stream") != PUBLIC_WS_CHANNEL_CANDLE:
            return None
        candle = self._to_candle(data.get("feed"))
        return [candle] if candle is not None else None
