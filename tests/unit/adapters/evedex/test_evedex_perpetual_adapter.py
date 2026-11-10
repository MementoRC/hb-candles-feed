"""Tests for the Evedex perpetual adapter (offline, fixture based)."""

import logging
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

    def test_ws_url_and_intervals(self, adapter):
        assert adapter.get_ws_url() == "wss://ws.evedex.com/connection/websocket"
        assert adapter.get_ws_supported_intervals() == list(INTERVALS)

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

    @pytest.mark.parametrize(
        ("start", "limit", "expected_before"),
        [
            (1706745600, 1, "2024-03-01T00:00:00.000Z"),  # Feb 2024 (leap): 29 days
            (1675209600, 1, "2023-03-01T00:00:00.000Z"),  # Feb 2023: 28 days
            (1675209600, 13, "2024-03-01T00:00:00.000Z"),  # Feb 2023 + 13 months across leap year
        ],
    )
    def test_monthly_window_spans_calendar_months(self, adapter, start, limit, expected_before):
        params = adapter._get_rest_params("BTC-USD", "1M", start_time=start, limit=limit)
        assert params["after"] == adapter._to_iso(start)
        assert params["before"] == expected_before

    def test_monthly_default_window_starts_n_months_back(self, adapter, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: 1710504000)  # 2024-03-15T12:00:00Z
        params = adapter._get_rest_params("BTC-USD", "1M", limit=13)
        assert params["after"] == "2023-02-01T00:00:00.000Z"
        assert params["before"] == "2024-03-15T12:00:00.000Z"

    def test_hourly_window_unchanged(self, adapter, monkeypatch):
        monkeypatch.setattr(time, "time", lambda: T0 + 123)
        params = adapter._get_rest_params("BTC-USD", "1h", start_time=T0 + 17, limit=5)
        assert params["after"] == "2024-01-01T00:00:17.000Z"
        assert params["before"] == "2024-01-01T05:00:17.000Z"
        params = adapter._get_rest_params("BTC-USD", "1h", limit=5)
        assert params["after"] == "2023-12-31T19:02:03.000Z"
        assert params["before"] == "2024-01-01T00:02:03.000Z"

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

    @pytest.mark.parametrize("empty", [[], {"data": []}])
    def test_empty_inputs(self, adapter, empty):
        assert adapter._parse_rest_response(empty) == []

    @pytest.mark.parametrize("bad", [None, {}, "x", {"data": "x"}])
    def test_unparseable_raises(self, adapter, bad):
        with pytest.raises(ValueError):
            adapter._parse_rest_response(bad)


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


def _push(data):
    return {"push": {"channel": "c", "pub": {"data": data}}}


class TestEvedexWebSocket:
    def test_connect_payload_resets_id_per_call(self, adapter):
        assert adapter.get_ws_connect_payload() == {"connect": {"name": "js"}, "id": 1}
        adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        assert adapter.get_ws_connect_payload() == {"connect": {"name": "js"}, "id": 1}

    async def test_subscription_payload_uses_resolved_instrument(self, adapter):
        client = TestEvedexFetch._client()
        adapter.get_ws_connect_payload()
        await adapter.prepare_ws_subscription("BTC-USDT", client)
        payload = adapter.get_ws_subscription_payload("BTC-USDT", "5m")
        assert payload == {
            "subscribe": {
                "channel": "market-data:last-candlestick-BTCUSD:PERP-5m",
                "recoverable": True,
                "flag": 1,
            },
            "id": 2,
        }
        assert adapter.get_ws_subscription_payload("BTC-USDT", "5m")["id"] == 3

    def test_subscription_payload_falls_back_to_derived_instrument(self, adapter):
        payload = adapter.get_ws_subscription_payload("SOL-USDT", "1h")
        assert payload["subscribe"]["channel"] == "market-data:last-candlestick-SOLUSD-1h"
        assert payload["id"] == 1

    def test_get_ws_reply(self, adapter):
        assert adapter.get_ws_reply({}) == {}
        assert adapter.get_ws_reply({"ping": {}}) == {"pong": {}}
        assert adapter.get_ws_reply(_push(ROWS_6[0])) is None
        assert adapter.get_ws_reply({"id": 1, "connect": {}}) is None

    def test_parse_push_with_dict_data(self, adapter):
        adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        row = {"t": T0 * 1000 + 7, "o": 1, "c": 2, "h": 3, "l": 0.5, "v": 4}
        (candle,) = adapter.parse_ws_message(_push(row))
        assert candle.timestamp == T0
        assert (candle.open, candle.close, candle.volume) == (1.0, 2.0, 4.0)

    def test_parse_push_with_list_row(self, adapter):
        adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        (candle,) = adapter.parse_ws_message(_push(ROWS_7[0]))
        assert candle.timestamp == T0 + 60
        assert candle.quote_asset_volume == 126450.0

    def test_parse_push_with_wrapped_list(self, adapter):
        adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        (candle,) = adapter.parse_ws_message(_push({"data": ROWS_6[0]}))
        assert candle.timestamp == T0

    def test_parse_top_level_data(self, adapter):
        (candle,) = adapter.parse_ws_message({"data": ROWS_6[0]})
        assert candle.timestamp == T0

    def test_non_numeric_values_drop_ws_push_and_rest_row(self, adapter):
        adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        bad = {"t": T0 * 1000, "o": "abc", "c": 2, "h": 3, "l": 1, "v": 4}
        assert adapter.parse_ws_message(_push(bad)) is None
        rows = [bad, ROWS_6[0]]
        assert len(adapter._parse_rest_response(rows, interval_seconds=60)) == 1

    @pytest.mark.parametrize("ts", [None, [1], {"a": 1}, 1e400, float("inf"), float("nan")])
    def test_bad_timestamp_type_or_overflow_drops_row(self, adapter, ts):
        row = [ts, "1", "2", "3", "0.5", "7"]
        assert adapter._row_to_candle(row, 60) is None

    def test_overflowing_timestamp_is_dropped(self, adapter):
        row = [10**400, "1", "2", "3", "0.5", "7"]
        assert adapter._row_to_candle(row, 60) is None

    @pytest.mark.parametrize("bad", ["nan", "inf", "-inf", float("nan"), float("inf")])
    @pytest.mark.parametrize("position", [1, 2, 3, 4, 5])
    def test_non_finite_values_drop_rest_row(self, adapter, bad, position):
        row = [T0 * 1000, "1", "2", "3", "0.5", "7"]
        row[position] = bad
        assert adapter._parse_rest_response([row, ROWS_6[0]], interval_seconds=60)[0].open == 1.0
        assert len(adapter._parse_rest_response([row], interval_seconds=60)) == 0

    @pytest.mark.parametrize("bad", ["nan", float("inf")])
    @pytest.mark.parametrize("key", ["o", "h", "l", "c", "v", "q"])
    def test_non_finite_values_drop_ws_push(self, adapter, bad, key):
        adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        row = {"t": T0 * 1000, "o": 1, "c": 2, "h": 3, "l": 0.5, "v": 4, "q": 5}
        row[key] = bad
        assert adapter.parse_ws_message(_push(row)) is None

    def test_error_reply_is_logged_and_dropped(self, adapter, caplog):
        message = {"id": 3, "error": {"code": 102, "message": "unknown channel"}}
        with caplog.at_level(logging.ERROR):
            assert adapter.parse_ws_message(message) is None
        assert "id=3" in caplog.text
        assert "code=102" in caplog.text
        assert "unknown channel" in caplog.text

    def test_success_replies_are_silent(self, adapter, caplog):
        with caplog.at_level(logging.DEBUG):
            assert adapter.parse_ws_message({"id": 1, "connect": {"client": "x"}}) is None
            assert adapter.parse_ws_message({"id": 2, "subscribe": {}}) is None
        assert caplog.text == ""

    @pytest.mark.parametrize(
        "message",
        [
            {"id": 1, "connect": {"client": "x"}},
            {"id": 2, "subscribe": {}},
            {},
            {"push": {"pub": {}}},
            {"push": {"pub": {"data": "x"}}},
            _push([1, 2]),
            None,
            "x",
        ],
    )
    def test_parse_ignores_non_candle_frames(self, adapter, message):
        assert adapter.parse_ws_message(message) is None


class TestEvedexRegistration:
    def test_registry_name(self):
        assert ExchangeRegistry.get_adapter_class("evedex_perpetual") is EvedexPerpetualAdapter

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP["evedex_perpetual"] == "evedex_perpetual"
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="evedex_perpetual", trading_pair="BTC-USDT")
        )
        assert candle.name == "evedex_perpetual"
