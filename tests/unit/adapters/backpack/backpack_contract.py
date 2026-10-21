"""Shared offline contract tests for the Backpack spot and perpetual adapters.

Concrete test modules subclass :class:`BackpackAdapterContract` and set the class attributes.
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.backpack.constants import (
    CANDLES_ENDPOINT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory

# 2024-01-01T00:00:00Z
T0 = 1704067200

# Shaped like GET /api/v1/klines (values are strings, timestamps naive UTC ISO-8601).
REST_FIXTURE = [
    {
        "start": "2024-01-01 00:00:00",
        "open": "42000.5",
        "high": "42100.0",
        "low": "41950.0",
        "close": "42050.0",
        "end": "2024-01-01 00:01:00",
        "volume": "12.5",
        "quoteVolume": "525000.25",
        "trades": "87",
    },
    {
        "start": "2024-01-01T00:01:00",
        "open": "42050.0",
        "high": "42200.0",
        "low": "42000.0",
        "close": "42150.0",
        "end": "2024-01-01T00:02:00",
        "volume": "3.0",
        "quoteVolume": "126000.0",
        "trades": 14,
    },
    # Empty bucket: no trades yet, null OHLC. Must be skipped.
    {
        "start": "2024-01-01T00:02:00",
        "open": None,
        "high": None,
        "low": None,
        "close": None,
        "end": "2024-01-01T00:03:00",
        "volume": "0",
        "quoteVolume": "0",
        "trades": "0",
    },
]

# Shaped like the kline.<interval>.<symbol> websocket stream.
WS_FIXTURE = {
    "stream": "kline.1m.BTC_USDC",
    "data": {
        "e": "kline",
        "E": 1704067230000000,
        "s": "BTC_USDC",
        "t": "2024-01-01T00:00:00",
        "T": "2024-01-01T00:01:00",
        "o": "42000.5",
        "c": "42050.0",
        "h": "42100.0",
        "l": "41950.0",
        "v": "2.0",
        "n": 9,
        "X": False,
    },
}


class BackpackAdapterContract:
    """Behaviour every Backpack adapter must satisfy."""

    ADAPTER_CLS: type
    SYMBOL: str  # expected exchange symbol for "BTC-USDC"
    REGISTRY_NAME: str
    CONNECTOR_NAME: str  # upstream hummingbot connector name

    @pytest.fixture
    def adapter(self):
        return self.ADAPTER_CLS()

    def test_symbol_conversion(self):
        assert self.ADAPTER_CLS.get_trading_pair_format("BTC-USDC") == self.SYMBOL

    def test_intervals(self, adapter):
        intervals = adapter.get_supported_intervals()
        assert intervals == INTERVALS
        assert len(intervals) == 16
        assert intervals["1s"] == 1
        assert intervals["3d"] == 3 * 86400
        assert intervals["1M"] == 2592000
        assert adapter.get_ws_supported_intervals() == WS_INTERVALS

    def test_urls(self, adapter):
        assert adapter._get_rest_url() == f"{REST_URL}{CANDLES_ENDPOINT}"
        assert adapter.get_ws_url() == WSS_URL

    def test_rest_params_with_start_time(self, adapter):
        params = adapter._get_rest_params("BTC-USDC", "1M", start_time=T0, limit=500)
        assert params == {"symbol": self.SYMBOL, "interval": "1month", "startTime": T0}

    @pytest.mark.parametrize("limit", [0, -3])
    def test_rest_params_non_positive_limit_means_one_interval(self, adapter, limit):
        before = int(time.time())
        params = adapter._get_rest_params("BTC-USDC", "1m", limit=limit)
        assert abs(params["startTime"] - (before - 60)) <= 5

    def test_rest_params_default_start_time_is_present(self, adapter):
        before = int(time.time())
        params = adapter._get_rest_params("BTC-USDC", "1m", limit=10)
        assert abs(params["startTime"] - (before - 600)) <= 5

    @pytest.mark.parametrize("limit", [None, 50000])
    def test_rest_params_limit_none_or_oversized_uses_max(self, adapter, limit):
        # RESTPollingStrategy.poll_once passes limit=None for incremental polls.
        before = int(time.time())
        params = adapter._get_rest_params("BTC-USDC", "1m", limit=limit)
        expected = before - MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST * 60
        assert abs(params["startTime"] - expected) <= 5

    def test_parse_rest_response_ten_columns_in_seconds(self, adapter):
        candles = adapter._parse_rest_response(REST_FIXTURE)
        assert len(candles) == 2  # null-open bucket dropped
        assert all(isinstance(c, CandleData) for c in candles)
        assert candles[0].to_array() == [
            float(T0),
            42000.5,
            42100.0,
            41950.0,
            42050.0,
            12.5,
            525000.25,
            87,
            0.0,
            0.0,
        ]
        assert candles[1].timestamp == T0 + 60
        assert candles[1].n_trades == 14

    @pytest.mark.skipif(not hasattr(time, "tzset"), reason="POSIX only")
    def test_naive_iso_is_utc_regardless_of_local_tz(self, adapter, monkeypatch):
        monkeypatch.setenv("TZ", "America/New_York")
        time.tzset()
        try:
            candles = adapter._parse_rest_response(REST_FIXTURE)
        finally:
            monkeypatch.undo()
            time.tzset()
        assert candles[0].timestamp == T0

    @pytest.mark.parametrize("null_field", ["high", "low", "close"])
    def test_parse_rest_response_skips_partial_ohlc_rows(self, adapter, null_field):
        partial = {**REST_FIXTURE[0], null_field: None}
        candles = adapter._parse_rest_response([partial, REST_FIXTURE[1]])
        assert [c.timestamp for c in candles] == [T0 + 60]

    @pytest.mark.parametrize("bad", [None, {}, "x", []])
    def test_parse_rest_response_empty_inputs(self, adapter, bad):
        assert adapter._parse_rest_response(bad) == []

    def test_ws_subscription_payload(self, adapter):
        assert adapter.get_ws_subscription_payload("BTC-USDC", "1M") == {
            "method": "SUBSCRIBE",
            "params": [f"kline.1month.{self.SYMBOL}"],
        }

    def test_parse_ws_message_quote_volume_is_derived(self, adapter):
        candles = adapter.parse_ws_message(WS_FIXTURE)
        assert candles is not None
        assert candles[0].to_array() == [
            float(T0),
            42000.5,
            42100.0,
            41950.0,
            42050.0,
            2.0,
            2.0 * 42050.0,
            9,
            0.0,
            0.0,
        ]

    def test_parse_ws_message_ignores_other_and_empty(self, adapter):
        assert adapter.parse_ws_message(None) is None
        assert adapter.parse_ws_message({"data": {"e": "trade"}}) is None
        empty = {"data": {**WS_FIXTURE["data"], "o": None}}
        assert adapter.parse_ws_message(empty) is None

    async def test_fetch_rest_candles(self, adapter):
        client = MagicMock()
        client.get_rest_data = AsyncMock(return_value=REST_FIXTURE)
        candles = await adapter.fetch_rest_candles(
            "BTC-USDC", "1m", start_time=T0, limit=100, network_client=client
        )
        assert len(candles) == 2
        client.get_rest_data.assert_awaited_once_with(
            url=f"{REST_URL}{CANDLES_ENDPOINT}",
            params={"symbol": self.SYMBOL, "interval": "1m", "startTime": T0},
        )

    def test_registry_lookup(self):
        assert ExchangeRegistry.get_adapter_class(self.REGISTRY_NAME) is self.ADAPTER_CLS

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP[self.CONNECTOR_NAME] == self.REGISTRY_NAME
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector=self.CONNECTOR_NAME, trading_pair="BTC-USDC")
        )
        assert candle.name == self.REGISTRY_NAME
