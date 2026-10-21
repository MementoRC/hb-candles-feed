"""Tests for the Evedex perpetual adapter (offline, fixture based)."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.evedex.constants import (
    CANDLES_ENDPOINT,
    EXCHANGE_REST_URL,
    INSTRUMENTS_ENDPOINT,
    INTERVALS,
    MARKET_DATA_REST_URL,
)
from candles_feed.adapters.evedex.perpetual_adapter import EvedexPerpetualAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory

T0 = 1704067200  # 2024-01-01T00:00:00Z, a multiple of every supported interval but 1M/1w

# Rows are [ts, open, close, high, low, volume_usd, volume] (7 cols) or without volume_usd (6 cols).
ROWS_7 = [
    [(T0 + 60) * 1000 + 17, "42050", "42150", "42200", "42000", "126450", "3.0"],
    [T0 * 1000 + 5, "42000.5", "42050", "42100", "41950", "525000.25", "12.5"],
]
ROWS_6 = [[T0 * 1000, "1", "2", "3", "0.5", "7"]]
ROWS_DICT = [
    {
        "time": T0 * 1000,
        "open": "1",
        "close": "2",
        "high": "3",
        "low": "0.5",
        "volume": "7",
        "volumeUsd": "14",
    },
    {"t": (T0 + 60) * 1000, "o": 2, "c": 3, "h": 4, "l": 1, "v": 5, "q": 15},
]

INSTRUMENTS = [
    {"name": "ETHUSD", "from": {"symbol": "ETH"}, "to": {"symbol": "USD"}},
    {"name": "BTCUSD:PERP", "from": {"symbol": "BTC"}, "to": {"symbol": "USD"}},
    {"name": "BTCEUR", "from": {"symbol": "BTC"}, "to": {"symbol": "EUR"}},
]


@pytest.fixture
def adapter():
    return EvedexPerpetualAdapter()


class TestEvedexStatic:
    def test_intervals(self, adapter):
        intervals = adapter.get_supported_intervals()
        assert intervals == INTERVALS
        assert len(intervals) == 15
        assert "1s" not in intervals
        assert intervals["1M"] == 2592000
        assert intervals["3d"] == 3 * 86400

    @pytest.mark.parametrize(
        ("pair", "expected"),
        [("BTC-USDT", "BTCUSD"), ("BTC-USD", "BTCUSD"), ("ETH-USDC", "ETHUSDC")],
    )
    def test_derived_symbol(self, pair, expected):
        assert EvedexPerpetualAdapter.get_trading_pair_format(pair) == expected

    def test_no_websocket(self, adapter):
        with pytest.raises(NotImplementedError):
            adapter.get_ws_url()
        with pytest.raises(NotImplementedError):
            adapter.get_ws_supported_intervals()

    def test_url_templates(self, adapter):
        assert adapter._get_rest_url() == f"{MARKET_DATA_REST_URL}{CANDLES_ENDPOINT}"
        assert (
            adapter._get_rest_url_for_pair("BTC-USDT")
            == f"{MARKET_DATA_REST_URL}/api/history/BTCUSD/list"
        )


class TestEvedexRestParams:
    def test_iso_after_before_with_millis_and_z(self, adapter):
        params = adapter._get_rest_params("BTC-USD", "5m", start_time=T0, limit=10)
        assert params == {
            "group": "5m",
            "after": "2024-01-01T00:00:00.000Z",
            "before": "2024-01-01T00:50:00.000Z",
        }

    def test_monthly_group(self, adapter):
        assert adapter._get_rest_params("BTC-USD", "1M", start_time=T0, limit=1)["group"] == "1M"

    def test_limit_none_and_oversized_cap_to_1000(self, adapter):
        for limit in (None, 99999):
            params = adapter._get_rest_params("BTC-USD", "1m", start_time=T0, limit=limit)
            assert params["before"] == "2024-01-01T16:40:00.000Z"

    @pytest.mark.parametrize("limit", [0, -3])
    def test_non_positive_limit_means_one_interval_window(self, adapter, limit):
        params = adapter._get_rest_params("BTC-USD", "1m", start_time=T0, limit=limit)
        assert params["after"] == "2024-01-01T00:00:00.000Z"
        assert params["before"] == "2024-01-01T00:01:00.000Z"

    def test_default_window_ends_now(self, adapter):
        now = time.time()
        params = adapter._get_rest_params("BTC-USD", "1m", limit=10)
        assert set(params) == {"group", "after", "before"}
        assert params["after"] < params["before"]
        assert params["before"].endswith("Z")
        year = time.gmtime(now).tm_year
        assert params["before"].startswith(str(year))


class TestEvedexParsing:
    def test_seven_column_rows_sorted_and_aligned(self, adapter):
        candles = adapter._parse_rest_response(ROWS_7, interval_seconds=60)
        assert [c.timestamp for c in candles] == [T0, T0 + 60]
        assert candles[0].to_array() == [
            float(T0),
            42000.5,
            42100.0,
            41950.0,
            42050.0,
            12.5,
            525000.25,
            0,
            0.0,
            0.0,
        ]

    def test_six_column_rows_have_zero_quote_volume(self, adapter):
        (candle,) = adapter._parse_rest_response(ROWS_6, interval_seconds=60)
        assert candle.to_array() == [float(T0), 1.0, 3.0, 0.5, 2.0, 7.0, 0.0, 0, 0.0, 0.0]

    def test_dict_rows_and_wrapped_payloads(self, adapter):
        for payload in (
            ROWS_DICT,
            {"data": ROWS_DICT},
            {"result": ROWS_DICT},
            {"candles": ROWS_DICT},
        ):
            candles = adapter._parse_rest_response(payload, interval_seconds=60)
            assert [c.timestamp for c in candles] == [T0, T0 + 60]
        assert candles[0].to_array() == [float(T0), 1.0, 3.0, 0.5, 2.0, 7.0, 14.0, 0, 0.0, 0.0]
        assert candles[1].quote_asset_volume == 15.0

    def test_nanosecond_timestamps(self, adapter):
        rows = [[T0 * 10**9 + 123, "1", "2", "3", "0.5", "7"]]
        (candle,) = adapter._parse_rest_response(rows, interval_seconds=60)
        assert candle.timestamp == T0

    def test_invalid_timestamp_row_is_skipped_not_fatal(self, adapter):
        rows = [{"t": 0, "o": 1, "c": 1, "h": 1, "l": 1, "v": 1}]
        assert adapter._parse_rest_response(rows, interval_seconds=60) == []

    def test_duplicate_buckets_keep_latest_row(self, adapter):
        rows = [
            [T0 * 1000 + 1, "1", "1", "1", "1", "1"],
            [T0 * 1000 + 2, "9", "9", "9", "9", "9"],
        ]
        (candle,) = adapter._parse_rest_response(rows, interval_seconds=60)
        assert candle.open == 9.0

    def test_without_interval_timestamps_are_only_converted(self, adapter):
        (candle,) = adapter._parse_rest_response(ROWS_7[1:])
        assert candle.timestamp == T0

    def test_malformed_rows_skipped(self, adapter):
        rows = [[T0 * 1000, "1"], "x", {"open": 1}, ROWS_6[0]]
        assert len(adapter._parse_rest_response(rows, interval_seconds=60)) == 1

    @pytest.mark.parametrize("bad", [None, {}, "x", [], {"data": "x"}])
    def test_empty_inputs(self, adapter, bad):
        assert adapter._parse_rest_response(bad) == []


class TestEvedexFetch:
    @staticmethod
    def _client(instruments=INSTRUMENTS, error=None, candles=ROWS_7):
        async def get_rest_data(url, params=None, data=None, headers=None, method="GET"):
            if url.endswith(INSTRUMENTS_ENDPOINT):
                if error:
                    raise error
                return instruments
            return candles

        client = MagicMock()
        client.get_rest_data = AsyncMock(side_effect=get_rest_data)
        return client

    async def test_weekly_candle_keeps_monday_timestamp(self, adapter):
        monday = 1704067200  # 2024-01-01T00:00:00Z, a Monday (not a multiple of 604800)
        client = self._client(candles=[[monday * 1000, "1", "2", "3", "0.5", "7"]])
        candles = await adapter.fetch_rest_candles(
            "BTC-USDT", "1w", start_time=monday, limit=5, network_client=client
        )
        assert [c.timestamp for c in candles] == [monday]

    async def test_monthly_candles_keep_exact_timestamps_and_stay_distinct(self, adapter):
        months = [1704067200, 1706745600, 1709251200]  # 2024-01-01, 02-01, 03-01 UTC
        rows = [[ts * 1000, "1", "2", "3", "0.5", "7"] for ts in months]
        client = self._client(candles=rows)
        candles = await adapter.fetch_rest_candles(
            "BTC-USDT", "1M", start_time=months[0], limit=5, network_client=client
        )
        assert [c.timestamp for c in candles] == months

    async def test_sub_day_interval_still_floors(self, adapter):
        rows = [[(T0 + 60) * 1000 + 17, "1", "2", "3", "0.5", "7"]]
        client = self._client(candles=rows)
        candles = await adapter.fetch_rest_candles(
            "BTC-USDT", "1m", start_time=T0, limit=5, network_client=client
        )
        assert [c.timestamp for c in candles] == [T0 + 60]

    async def test_resolves_instrument_name_then_fetches(self, adapter):
        client = self._client()
        candles = await adapter.fetch_rest_candles(
            "BTC-USDT", "1m", start_time=T0, limit=10, network_client=client
        )
        assert all(isinstance(c, CandleData) for c in candles)
        assert [c.timestamp for c in candles] == [T0, T0 + 60]
        first, second = client.get_rest_data.await_args_list
        assert first.kwargs["url"] == f"{EXCHANGE_REST_URL}{INSTRUMENTS_ENDPOINT}"
        assert second.kwargs["url"] == f"{MARKET_DATA_REST_URL}/api/history/BTCUSD:PERP/list"
        assert second.kwargs["params"]["group"] == "1m"

    async def test_instrument_list_wrapper_and_cached_resolution(self, adapter):
        client = self._client(instruments={"list": INSTRUMENTS})
        for _ in range(2):
            await adapter.fetch_rest_candles(
                "BTC-USDT", "1m", start_time=T0, limit=10, network_client=client
            )
        urls = [c.kwargs["url"] for c in client.get_rest_data.await_args_list]
        assert sum(u.endswith(INSTRUMENTS_ENDPOINT) for u in urls) == 1

    async def test_usdt_resolves_to_usd_but_exact_quote_wins_for_others(self, adapter):
        client = self._client()
        await adapter.fetch_rest_candles(
            "BTC-EUR", "1m", start_time=T0, limit=10, network_client=client
        )
        assert client.get_rest_data.await_args_list[1].kwargs["url"].endswith("/BTCEUR/list")

    async def test_unresolved_pair_uses_derived_symbol(self, adapter):
        client = self._client()
        await adapter.fetch_rest_candles(
            "SOL-USDT", "1m", start_time=T0, limit=10, network_client=client
        )
        assert client.get_rest_data.await_args_list[1].kwargs["url"].endswith("/SOLUSD/list")

    async def test_lookup_failure_falls_back_and_is_retried(self, adapter):
        client = self._client(error=RuntimeError("down"))
        for _ in range(2):
            candles = await adapter.fetch_rest_candles(
                "BTC-USDT", "1m", start_time=T0, limit=10, network_client=client
            )
            assert len(candles) == 2
        urls = [c.kwargs["url"] for c in client.get_rest_data.await_args_list]
        assert sum(u.endswith(INSTRUMENTS_ENDPOINT) for u in urls) == 2
        assert urls[1].endswith("/BTCUSD/list")

    async def test_requires_network_client(self, adapter):
        with pytest.raises(ValueError, match="network_client"):
            await adapter.fetch_rest_candles("BTC-USDT", "1m")


class TestEvedexRegistration:
    def test_registry_name(self):
        assert ExchangeRegistry.get_adapter_class("evedex_perpetual") is EvedexPerpetualAdapter

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP["evedex_perpetual"] == "evedex_perpetual"
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="evedex_perpetual", trading_pair="BTC-USDT")
        )
        assert candle.name == "evedex_perpetual"
