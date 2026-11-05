"""Tests for the GRVT perpetual adapter (offline, fixture based)."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.grvt.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    KLINE_PATH_URL,
    MAINNET_REST_URL,
    MAINNET_WSS_URL,
    PUBLIC_WS_CHANNEL_CANDLE,
    TESTNET_REST_URL,
    TESTNET_WSS_URL,
)
from candles_feed.adapters.grvt.perpetual_adapter import GrvtPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_config import NetworkConfig, NetworkEnvironment
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory

T0 = 1704067200  # 2024-01-01T00:00:00Z
NS = 1_000_000_000
INSTRUMENT = "BTC_USDT_Perp"

# Shaped like POST full/v1/kline: {"result": [...]}, open_time in ns (string), unsorted.
REST_FIXTURE = {
    "result": [
        {
            "open_time": str((T0 + 60) * NS),
            "close_time": str((T0 + 120) * NS - 1),
            "open": "42050.0",
            "close": "42150.0",
            "high": "42200.0",
            "low": "42000.0",
            "volume_b": "3.0",
            "volume_q": "126450.0",
            "trades": 14,
            "instrument": INSTRUMENT,
        },
        {
            "open_time": str(T0 * NS),
            "close_time": str((T0 + 60) * NS - 1),
            "open": "42000.5",
            "close": "42050.0",
            "high": "42100.0",
            "low": "41950.0",
            "volume_b": "12.5",
            "volume_q": "525000.25",
            "trades": 87,
            "instrument": INSTRUMENT,
        },
    ]
}

WS_FIXTURE = {
    "stream": "v1.candle",
    "selector": f"{INSTRUMENT}@CI_1_M-TRADE",
    "sequence_number": "5",
    "feed": REST_FIXTURE["result"][1],
}


@pytest.fixture
def adapter():
    return GrvtPerpetualAdapter()


class TestGrvtStatic:
    def test_intervals(self, adapter):
        intervals = adapter.get_supported_intervals()
        assert intervals == INTERVALS
        assert len(intervals) == 14
        assert "1s" not in intervals
        assert "1M" not in intervals
        assert intervals["3d"] == 3 * 86400

    def test_symbol(self):
        assert GrvtPerpetualAdapter.get_trading_pair_format("BTC-USDT") == INSTRUMENT

    def test_urls_mainnet_and_testnet(self):
        assert GrvtPerpetualAdapter()._get_rest_url() == f"{MAINNET_REST_URL}/{KLINE_PATH_URL}"
        assert GrvtPerpetualAdapter().get_ws_url() == MAINNET_WSS_URL
        testnet = GrvtPerpetualAdapter(
            network_config=NetworkConfig(default_environment=NetworkEnvironment.TESTNET)
        )
        assert testnet._get_rest_url() == f"{TESTNET_REST_URL}/{KLINE_PATH_URL}"
        assert testnet.get_ws_url() == TESTNET_WSS_URL

    def test_connector_values_copied(self):
        assert KLINE_PATH_URL == "full/v1/kline"
        assert PUBLIC_WS_CHANNEL_CANDLE == "v1.candle"
        assert MAINNET_REST_URL == "https://market-data.grvt.io"
        assert MAINNET_WSS_URL == "wss://market-data.grvt.io/ws/full"
        assert INTERVAL_TO_EXCHANGE_FORMAT["1m"] == "CI_1_M"
        assert INTERVAL_TO_EXCHANGE_FORMAT["1w"] == "CI_1_W"
        assert set(INTERVAL_TO_EXCHANGE_FORMAT) == set(INTERVALS)


class TestGrvtRestBody:
    def test_body_uses_ns_strings_and_interval_codes(self, adapter):
        body = adapter._get_rest_params("BTC-USDT", "1m", start_time=T0, limit=10)
        assert body == {
            "instrument": INSTRUMENT,
            "interval": "CI_1_M",
            "type": "TRADE",
            "start_time": str(T0 * NS),
            "end_time": str((T0 + 10 * 60) * NS),
            "limit": 11,  # window [start, end] spans limit + 1 buckets
        }

    def test_ns_conversion_is_exact_integer_math(self, adapter):
        # float(start) * 1e9 loses precision above 2**53; integer math does not.
        start = 1_900_000_001
        body = adapter._get_rest_params("BTC-USDT", "1m", start_time=start, limit=1)
        assert body["start_time"] == "1900000001000000000"
        assert body["end_time"] == "1900000061000000000"

    @pytest.mark.parametrize("limit", [None, 5000])
    def test_limit_capped_at_1000(self, adapter, limit):
        body = adapter._get_rest_params("BTC-USDT", "1m", start_time=T0, limit=limit)
        assert body["limit"] == 1000

    @pytest.mark.parametrize("limit", [0, -3])
    def test_non_positive_limit_means_one_interval_window(self, adapter, limit):
        now = time.time()
        body = adapter._get_rest_params("BTC-USDT", "1m", limit=limit)
        assert int(body["end_time"]) - int(body["start_time"]) == 60 * NS
        assert abs(int(body["start_time"]) / NS - (now - 60)) < 5

    def test_default_window_ends_now(self, adapter):
        now = time.time()
        body = adapter._get_rest_params("BTC-USDT", "1h", limit=24)
        assert abs(int(body["end_time"]) / NS - now) < 5
        assert int(body["end_time"]) - int(body["start_time"]) == 24 * 3600 * NS


class TestGrvtParsing:
    def test_parse_sorted_ten_columns_in_seconds(self, adapter):
        candles = adapter._parse_rest_response(REST_FIXTURE)
        assert all(isinstance(c, CandleData) for c in candles)
        assert [c.timestamp for c in candles] == [T0, T0 + 60]
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

    def test_rows_missing_fields_are_skipped(self, adapter):
        rows = {"result": [{"open_time": str(T0 * NS)}, REST_FIXTURE["result"][1]]}
        assert len(adapter._parse_rest_response(rows)) == 1

    def test_parse_empty_result(self, adapter):
        assert adapter._parse_rest_response({"result": []}) == []

    @pytest.mark.parametrize("bad", [None, {}, [], "x", {"result": None}, {"result": "x"}])
    def test_parse_unparseable_raises(self, adapter, bad):
        with pytest.raises(ValueError):
            adapter._parse_rest_response(bad)

    def test_ws_payload(self, adapter):
        first = adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        second = adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        assert first["jsonrpc"] == "2.0"
        assert first["method"] == "subscribe"
        assert first["params"] == {
            "stream": "v1.candle",
            "selectors": [f"{INSTRUMENT}@CI_1_M-TRADE"],
        }
        assert second["id"] == first["id"] + 1

    def test_ws_parse(self, adapter):
        (candle,) = adapter.parse_ws_message(WS_FIXTURE)
        assert candle.to_array()[:8] == [
            float(T0),
            42000.5,
            42100.0,
            41950.0,
            42050.0,
            12.5,
            525000.25,
            87,
        ]

    def test_ws_ignores_other_messages(self, adapter):
        assert adapter.parse_ws_message(None) is None
        assert adapter.parse_ws_message({"stream": "v1.ticker.s", "feed": {}}) is None
        assert adapter.parse_ws_message({"stream": "v1.candle"}) is None
        assert adapter.parse_ws_message({"jsonrpc": "2.0", "result": {}, "id": 1}) is None


class TestGrvtFetch:
    async def test_posts_json_body(self, adapter):
        client = MagicMock()
        client.get_rest_data = AsyncMock(return_value=REST_FIXTURE)
        candles = await adapter.fetch_rest_candles(
            "BTC-USDT", "1m", start_time=T0, limit=10, network_client=client
        )
        assert [c.timestamp for c in candles] == [T0, T0 + 60]
        client.get_rest_data.assert_awaited_once_with(
            url=f"{MAINNET_REST_URL}/{KLINE_PATH_URL}",
            data=adapter._get_rest_params("BTC-USDT", "1m", start_time=T0, limit=10),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    async def test_limit_plus_one_rows_are_trimmed_to_earliest_limit(self, adapter):
        # Inclusive window bounds make the exchange return limit + 1 rows.
        limit = 10
        rows = [
            {**REST_FIXTURE["result"][1], "open_time": str((T0 + i * 60) * NS)}
            for i in range(limit + 1)
        ]
        client = MagicMock()
        client.get_rest_data = AsyncMock(return_value={"result": list(reversed(rows))})
        candles = await adapter.fetch_rest_candles(
            "BTC-USDT", "1m", start_time=T0, limit=limit, network_client=client
        )
        assert [c.timestamp for c in candles] == [T0 + i * 60 for i in range(limit)]

    async def test_requires_network_client(self, adapter):
        with pytest.raises(ValueError, match="network_client"):
            await adapter.fetch_rest_candles("BTC-USDT", "1m")


class TestGrvtRegistration:
    def test_registry_name(self):
        assert ExchangeRegistry.get_adapter_class("grvt_perpetual") is GrvtPerpetualAdapter

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP["grvt_perpetual"] == "grvt_perpetual"
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="grvt_perpetual", trading_pair="BTC-USDT")
        )
        assert candle.name == "grvt_perpetual"
