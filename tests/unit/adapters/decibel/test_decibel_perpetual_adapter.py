"""Tests for the Decibel perpetual adapter (offline, fixture based)."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.decibel.constants import (
    CANDLES_ENDPOINT,
    INTERVALS,
    MAINNET_REST_URL,
    MAINNET_WSS_URL,
    MARKETS_ENDPOINT,
    NETNA_DOMAIN,
    NETNA_REST_URL,
    NETNA_WSS_URL,
    TESTNET_REST_URL,
    TESTNET_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.adapters.decibel.perpetual_adapter import DecibelPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_config import NetworkConfig, NetworkEnvironment
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory

T0 = 1704067200  # 2024-01-01T00:00:00Z
MARKET_ADDR = "0xabc123def456"

# Shaped like GET /api/v1/candlesticks (ms timestamps, string prices).
REST_FIXTURE = [
    {
        "t": T0 * 1000,
        "T": T0 * 1000 + 59999,
        "o": "42000.5",
        "h": "42100.0",
        "l": "41950.0",
        "c": "42050.0",
        "v": "12.5",
        "i": "1m",
    },
    {
        "t": (T0 + 60) * 1000,
        "T": (T0 + 60) * 1000 + 59999,
        "o": "42050.0",
        "h": "42200.0",
        "l": "42000.0",
        "c": "42150.0",
        "v": "3.0",
        "i": "1m",
    },
]

MARKETS_FIXTURE = [
    {"market_addr": "0xother", "market_name": "ETH/USD"},
    {"market_addr": MARKET_ADDR, "market_name": "BTC/USD"},
]

WS_FIXTURE = {
    "topic": f"market_candlestick:{MARKET_ADDR}:1m",
    "data": REST_FIXTURE[0],
}


@pytest.fixture
def adapter():
    return DecibelPerpetualAdapter()


class TestDecibelStatic:
    def test_intervals(self, adapter):
        intervals = adapter.get_supported_intervals()
        assert intervals == INTERVALS
        assert len(intervals) == 11
        for missing in ("1s", "6h", "3d", "1w", "1M"):
            assert missing not in intervals
        assert intervals["8h"] == 28800
        assert adapter.get_ws_supported_intervals() == WS_INTERVALS

    def test_symbol(self):
        assert DecibelPerpetualAdapter.get_trading_pair_format("BTC-USD") == "BTC/USD"

    def test_timestamp_unit_is_milliseconds(self, adapter):
        assert adapter.convert_timestamp_to_exchange(T0) == T0 * 1000


class TestDecibelDomains:
    def test_mainnet_default(self, adapter):
        assert adapter._get_rest_url() == f"{MAINNET_REST_URL}{CANDLES_ENDPOINT}"
        assert adapter.get_ws_url() == MAINNET_WSS_URL

    def test_netna(self):
        adapter = DecibelPerpetualAdapter(domain=NETNA_DOMAIN)
        assert adapter._get_rest_url() == f"{NETNA_REST_URL}{CANDLES_ENDPOINT}"
        assert adapter.get_ws_url() == NETNA_WSS_URL

    def test_testnet_via_network_config(self):
        adapter = DecibelPerpetualAdapter(
            network_config=NetworkConfig(default_environment=NetworkEnvironment.TESTNET)
        )
        assert adapter._get_rest_url() == f"{TESTNET_REST_URL}{CANDLES_ENDPOINT}"
        assert adapter.get_ws_url() == TESTNET_WSS_URL

    def test_unknown_domain_rejected(self):
        with pytest.raises(ValueError, match="domain"):
            DecibelPerpetualAdapter(domain="nope")


class TestDecibelRestParams:
    def test_params_use_name_until_market_resolved(self, adapter):
        params = adapter._get_rest_params("BTC-USD", "5m", start_time=T0, limit=100)
        assert params == {
            "market": "BTC/USD",
            "interval": "5m",
            "startTime": T0 * 1000,
            "endTime": (T0 + 100 * 300) * 1000,
        }

    def test_no_limit_param_is_sent(self, adapter):
        assert "limit" not in adapter._get_rest_params("BTC-USD", "1m", start_time=T0, limit=5)

    def test_limit_none_and_oversized_use_max_window(self, adapter):
        for limit in (None, 5000):
            params = adapter._get_rest_params("BTC-USD", "1m", start_time=T0, limit=limit)
            assert params["endTime"] - params["startTime"] == 1000 * 60 * 1000

    @pytest.mark.parametrize("limit", [0, -3])
    def test_non_positive_limit_means_one_interval_window(self, adapter, limit):
        before = int(time.time())
        params = adapter._get_rest_params("BTC-USD", "1m", limit=limit)
        assert params["endTime"] - params["startTime"] == 60 * 1000
        assert abs(params["startTime"] // 1000 - (before - 60)) <= 5

    def test_default_start_time(self, adapter):
        before = int(time.time())
        params = adapter._get_rest_params("BTC-USD", "1m", limit=10)
        assert abs(params["endTime"] // 1000 - before) <= 5
        assert params["endTime"] - params["startTime"] == 10 * 60 * 1000


class TestDecibelParsing:
    def test_parse_rest_ten_columns_in_seconds(self, adapter):
        candles = adapter._parse_rest_response(REST_FIXTURE)
        assert all(isinstance(c, CandleData) for c in candles)
        assert candles[0].to_array() == [
            float(T0),
            42000.5,
            42100.0,
            41950.0,
            42050.0,
            12.5,
            0.0,
            0,
            0.0,
            0.0,
        ]
        assert candles[1].timestamp == T0 + 60

    def test_parse_rest_accepts_wrapped_and_long_keys(self, adapter):
        row = {
            "timestamp": T0 * 1000,
            "open": 1,
            "high": 2,
            "low": 0.5,
            "close": 1.5,
            "volume": 9,
            "quote_volume": 13.5,
            "n_trades": 4,
        }
        (candle,) = adapter._parse_rest_response({"data": [row]})
        assert candle.to_array() == [float(T0), 1.0, 2.0, 0.5, 1.5, 9.0, 13.5, 4, 0.0, 0.0]

    def test_rows_missing_timestamp_or_prices_are_skipped_not_zeroed(self, adapter):
        rows = [
            {"o": "1", "h": "1", "l": "1", "c": "1", "v": "1"},
            {"t": T0 * 1000},
            REST_FIXTURE[0],
        ]
        candles = adapter._parse_rest_response(rows)
        assert [c.timestamp for c in candles] == [T0]

    @pytest.mark.parametrize("bad", [None, {}, "x", []])
    def test_parse_rest_empty(self, adapter, bad):
        assert adapter._parse_rest_response(bad) == []

    def test_ws_subscription_payload_uses_resolved_address(self, adapter):
        adapter._market_addrs["BTC-USD"] = MARKET_ADDR
        assert adapter.get_ws_subscription_payload("BTC-USD", "1m") == {
            "method": "subscribe",
            "topic": f"market_candlestick:{MARKET_ADDR}:1m",
        }

    def test_ws_subscription_without_address_raises_instead_of_name_fallback(self, adapter):
        assert adapter._market_addrs == {}
        with pytest.raises((ValueError, RuntimeError, LookupError)):
            adapter.get_ws_subscription_payload("BTC-USD", "1m")

    def test_ws_parse(self, adapter):
        (candle,) = adapter.parse_ws_message(WS_FIXTURE)
        assert candle.timestamp == T0
        assert candle.close == 42050.0

    def test_ws_ignores_other_topics_and_garbage(self, adapter):
        assert adapter.parse_ws_message(None) is None
        assert adapter.parse_ws_message({"topic": "trades:x", "data": REST_FIXTURE[0]}) is None
        assert adapter.parse_ws_message({"topic": "market_candlestick:x:1m", "data": {}}) is None
        assert adapter.parse_ws_message({"topic": "market_candlestick:x:1m"}) is None


class TestDecibelFetch:
    @staticmethod
    def _client(markets=MARKETS_FIXTURE, markets_error=None):
        async def get_rest_data(url, params=None, data=None, headers=None, method="GET"):
            if url.endswith(MARKETS_ENDPOINT):
                if markets_error:
                    raise markets_error
                return markets
            return REST_FIXTURE

        client = MagicMock()
        client.get_rest_data = AsyncMock(side_effect=get_rest_data)
        return client

    async def test_resolves_market_address_once(self, adapter):
        client = self._client()
        for _ in range(2):
            candles = await adapter.fetch_rest_candles(
                "BTC-USD", "1m", start_time=T0, limit=50, network_client=client
            )
            assert len(candles) == 2
        urls = [c.kwargs["url"] for c in client.get_rest_data.await_args_list]
        assert urls.count(f"{MAINNET_REST_URL}{MARKETS_ENDPOINT}") == 1
        candle_call = client.get_rest_data.await_args_list[1]
        assert candle_call.kwargs["url"] == f"{MAINNET_REST_URL}{CANDLES_ENDPOINT}"
        assert candle_call.kwargs["params"]["market"] == MARKET_ADDR
        assert adapter.get_ws_subscription_payload("BTC-USD", "1m")["topic"] == (
            f"market_candlestick:{MARKET_ADDR}:1m"
        )

    async def test_market_lookup_failure_falls_back_to_name_and_retries_later(self, adapter):
        client = self._client(markets_error=RuntimeError("boom"))
        candles = await adapter.fetch_rest_candles(
            "BTC-USD", "1m", start_time=T0, limit=50, network_client=client
        )
        assert len(candles) == 2
        assert client.get_rest_data.await_args_list[1].kwargs["params"]["market"] == "BTC/USD"
        await adapter.fetch_rest_candles(
            "BTC-USD", "1m", start_time=T0, limit=50, network_client=client
        )
        market_calls = [
            c
            for c in client.get_rest_data.await_args_list
            if c.kwargs["url"].endswith(MARKETS_ENDPOINT)
        ]
        assert len(market_calls) == 2

    @pytest.mark.parametrize(
        "client_kwargs",
        [{"markets_error": RuntimeError("boom")}, {"markets": []}],
        ids=["lookup_error", "market_not_listed"],
    )
    async def test_failed_lookup_never_yields_name_based_ws_topic(self, adapter, client_kwargs):
        client = self._client(**client_kwargs)
        await adapter.prepare_ws_subscription("BTC-USD", client)
        assert "BTC-USD" not in adapter._market_addrs
        with pytest.raises((ValueError, RuntimeError, LookupError)):
            adapter.get_ws_subscription_payload("BTC-USD", "1m")

    async def test_prepare_ws_subscription_enables_address_topic(self, adapter):
        await adapter.prepare_ws_subscription("BTC-USD", self._client())
        assert adapter.get_ws_subscription_payload("BTC-USD", "1m")["topic"] == (
            f"market_candlestick:{MARKET_ADDR}:1m"
        )

    async def test_api_key_sent_as_bearer_header(self):
        adapter = DecibelPerpetualAdapter(api_key="secret")
        client = self._client()
        await adapter.fetch_rest_candles(
            "BTC-USD", "1m", start_time=T0, limit=50, network_client=client
        )
        for call in client.get_rest_data.await_args_list:
            assert call.kwargs["headers"] == {"Authorization": "Bearer secret"}

    async def test_requires_network_client(self, adapter):
        with pytest.raises(ValueError, match="network_client"):
            await adapter.fetch_rest_candles("BTC-USD", "1m")


class TestDecibelRegistration:
    def test_registry_name(self):
        assert ExchangeRegistry.get_adapter_class("decibel_perpetual") is DecibelPerpetualAdapter

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP["decibel_perpetual"] == "decibel_perpetual"
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="decibel_perpetual", trading_pair="BTC-USD")
        )
        assert candle.name == "decibel_perpetual"
