"""
Decibel perpetual exchange adapter for the Candle Feed framework.

Decibel addresses candle queries by on-chain market address, not by market name.
The upstream connector derives the address with the ``decibel`` SDK; this adapter
resolves it from the public markets REST endpoint instead (no extra dependency).
"""

import logging
import time
from typing import Any, override

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_config import EndpointType, NetworkConfig
from candles_feed.core.protocols import NetworkClientProtocol
from candles_feed.core.rate_limiter import RestRateLimit

from .constants import (
    CANDLES_ENDPOINT,
    DEFAULT_DOMAIN,
    DOMAIN_TO_URLS,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MARKETS_ENDPOINT,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    TESTNET_DOMAIN,
    WS_CANDLES_CHANNEL,
    WS_INTERVALS,
)

_TIMESTAMP_KEYS = ("t", "timestamp")
_FIELD_KEYS = {
    "open": ("o", "open"),
    "high": ("h", "high"),
    "low": ("l", "low"),
    "close": ("c", "close"),
}


def _first(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return the first non-None value found under ``keys`` (None when absent)."""
    for key in keys:
        if row.get(key) is not None:
            return row[key]
    return None


@ExchangeRegistry.register("decibel_perpetual")
class DecibelPerpetualAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Decibel perpetual exchange adapter.

    Trading pair format: "BTC-USD" -> "BTC/USD". Timestamps: milliseconds.
    """

    TIMESTAMP_UNIT: str = "milliseconds"
    MAX_CANDLES_PER_REQUEST = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST

    # hummingbot/data_feed/candles_feed/decibel_perpetual_candles/constants.py:51,60 — 400 req/60s pool, candles cost 1
    REST_RATE_LIMIT = RestRateLimit(max_requests=400, period_seconds=60)

    def __init__(
        self,
        *args: Any,
        network_config: NetworkConfig | None = None,
        domain: str = DEFAULT_DOMAIN,
        api_key: str | None = None,
        **kwargs: Any,
    ):
        """Initialize the adapter.

        :param network_config: A testnet CANDLES environment selects the testnet domain
        :param domain: Mainnet (default), netna or testnet domain name
        :param api_key: Optional API key, sent as a Bearer token on REST requests
        :raises ValueError: If the domain is unknown
        """
        super().__init__()
        if network_config is not None and network_config.is_testnet_for(EndpointType.CANDLES):
            domain = TESTNET_DOMAIN
        if domain not in DOMAIN_TO_URLS:
            raise ValueError(f"Unknown Decibel domain: {domain}")
        self.network_config = network_config
        self._domain = domain
        self._api_key = api_key
        self._market_addrs: dict[str, str] = {}
        self._logger = logging.getLogger(__name__)

    @property
    def _rest_base(self) -> str:
        return DOMAIN_TO_URLS[self._domain][0]

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert "BTC-USD" to Decibel's market name "BTC/USD"."""
        return trading_pair.replace("-", "/", 1)

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
        """Get WebSocket URL for the configured domain."""
        return DOMAIN_TO_URLS[self._domain][1]

    @override
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles."""
        return f"{self._rest_base}{CANDLES_ENDPOINT}"

    def _market_param(self, trading_pair: str) -> str:
        """Resolved market address when known, else the market name."""
        return self._market_addrs.get(trading_pair, self.get_trading_pair_format(trading_pair))

    @override
    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for the REST request (times in ms; no limit parameter exists).

        The window is ``[start, start + limit * interval]``. Without ``start_time``
        the window ends now.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Number of candles wanted (capped to the maximum window)
        :returns: Request parameters
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
            "market": self._market_param(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "startTime": int(self.convert_timestamp_to_exchange(start_s)),
            "endTime": int(self.convert_timestamp_to_exchange(end_s)),
        }

    @staticmethod
    def _parse_row(row: Any) -> CandleData | None:
        """Parse one candle dict; rows lacking a timestamp or any OHLC value are dropped."""
        if not isinstance(row, dict):
            return None
        timestamp = _first(row, _TIMESTAMP_KEYS)
        values = {name: _first(row, keys) for name, keys in _FIELD_KEYS.items()}
        if timestamp is None or any(v is None for v in values.values()):
            return None
        volume = _first(row, ("v", "volume"))
        return CandleData(
            timestamp_raw=BaseAdapter.ensure_timestamp_in_seconds(timestamp),
            open=float(values["open"]),
            high=float(values["high"]),
            low=float(values["low"]),
            close=float(values["close"]),
            volume=float(volume) if volume is not None else 0.0,
            quote_asset_volume=float(_first(row, ("quote_volume",)) or 0.0),
            n_trades=int(_first(row, ("n_trades", "n")) or 0),
            taker_buy_base_volume=0.0,
            taker_buy_quote_volume=0.0,
        )

    @override
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse the REST response (a list, or a dict wrapping it under "data")."""
        rows = data.get("data") if isinstance(data, dict) else data
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise self._bad_response(data)
        return [candle for candle in map(self._parse_row, rows) if candle is not None]

    async def _resolve_market_address(
        self, trading_pair: str, network_client: NetworkClientProtocol
    ) -> None:
        """Resolve and cache the market address; on failure keep using the market name."""
        if trading_pair in self._market_addrs:
            return
        name = self.get_trading_pair_format(trading_pair)
        try:
            markets = await network_client.get_rest_data(
                url=f"{self._rest_base}{MARKETS_ENDPOINT}", headers=self._headers()
            )
        except Exception as e:
            self._logger.warning(f"Could not resolve Decibel market address for {name}: {e}")
            return
        rows = markets.get("data") if isinstance(markets, dict) else markets
        for market in rows if isinstance(rows, list) else []:
            if isinstance(market, dict) and market.get("market_name") == name:
                address = market.get("market_addr")
                if address:
                    self._market_addrs[trading_pair] = str(address)
                return

    def _headers(self) -> dict[str, str] | None:
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else None

    @override
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int | None = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles, resolving the market address first (once per pair)."""
        if network_client is None:
            raise ValueError("network_client is required for async operations")
        await self._resolve_market_address(trading_pair, network_client)
        response = await network_client.get_rest_data(
            url=self._get_rest_url(),
            params=self._get_rest_params(trading_pair, interval, start_time, limit),
            headers=self._headers(),
        )
        return self._parse_rest_response(response)

    async def prepare_ws_subscription(
        self, trading_pair: str, network_client: NetworkClientProtocol
    ) -> None:
        """Resolve the market address before subscribing (the WS topic requires it)."""
        await self._resolve_market_address(trading_pair, network_client)

    @override
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get the subscription payload.

        The WS topic needs the market address, so the name fallback is not used.

        :raises ValueError: If the market address has not been resolved
        """
        address = self._market_addrs.get(trading_pair)
        if address is None:
            raise ValueError(f"Decibel market address for {trading_pair} is not resolved")
        exchange_interval = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        return {
            "method": "subscribe",
            "topic": f"{WS_CANDLES_CHANNEL}:{address}:{exchange_interval}",
        }

    @override
    def parse_ws_message(self, data: dict[str, Any] | None) -> list[CandleData] | None:
        """Parse a ``market_candlestick`` update; other messages return None."""
        if not isinstance(data, dict) or WS_CANDLES_CHANNEL not in str(data.get("topic", "")):
            return None
        candle = self._parse_row(data.get("data"))
        return [candle] if candle is not None else None
