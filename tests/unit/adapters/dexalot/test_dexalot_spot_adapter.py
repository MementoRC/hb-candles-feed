"""Tests for the DexalotSpotAdapter (offline, fixture based).

Dexalot has no 1m candles, so the shared BaseAdapterTest contract does not apply.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.dexalot.constants import (
    CANDLES_ENDPOINT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.adapters.dexalot.spot_adapter import DexalotSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory

T0 = 1704067200  # 2024-01-01T00:00:00Z
PAIR = "ALOT-USDC"


def candle(date: str = "2024-01-01T00:00:00.000Z", **overrides) -> dict:
    """One row shaped like GET /trading/candlechart."""
    row = {
        "pair": "ALOT/USDC",
        "date": date,
        "open": 0.85,
        "high": 0.9,
        "low": 0.8,
        "close": 0.88,
        "volume": 1520.5,
    }
    return {**row, **overrides}


@pytest.fixture
def adapter() -> DexalotSpotAdapter:
    return DexalotSpotAdapter()


def test_symbol_uses_slash_separator():
    assert DexalotSpotAdapter.get_trading_pair_format(PAIR) == "ALOT/USDC"


def test_urls(adapter):
    assert adapter._get_rest_url() == f"{REST_URL}{CANDLES_ENDPOINT}"
    assert adapter.get_ws_url() == WSS_URL


def test_supported_intervals(adapter):
    assert adapter.get_supported_intervals() == INTERVALS
    assert list(INTERVALS) == ["5m", "15m", "30m", "1h", "4h", "1d"]
    assert adapter.get_ws_supported_intervals() == WS_INTERVALS == list(INTERVALS)


@pytest.mark.parametrize(
    ("interval", "num", "unit"),
    [
        ("5m", "5", "minute"),
        ("15m", "15", "minute"),
        ("30m", "30", "minute"),
        ("1h", "1", "hour"),
        ("4h", "4", "hour"),
        ("1d", "1", "day"),
    ],
)
def test_interval_is_split_into_number_and_unit(adapter, interval, num, unit):
    params = adapter._get_rest_params(PAIR, interval)
    assert (params["intervalnum"], params["intervalstr"]) == (num, unit)
    assert params["pair"] == "ALOT/USDC"


def test_window_is_iso_8601_and_limit_is_not_sent(adapter):
    params = adapter._get_rest_params(PAIR, "5m", start_time=T0, limit=100)
    assert params == {
        "pair": "ALOT/USDC",
        "intervalnum": "5",
        "intervalstr": "minute",
        "periodfrom": "2024-01-01T00:00:00Z",
        "periodto": "2024-01-01T08:20:00Z",  # 100 * 300 s later
    }


def test_without_start_time_there_is_no_window(adapter):
    params = adapter._get_rest_params(PAIR, "1h")
    assert "periodfrom" not in params
    assert "periodto" not in params


def test_max_candles_per_request():
    assert (
        DexalotSpotAdapter.MAX_CANDLES_PER_REQUEST
        == MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST
        == 1000
    )


def test_parse_rest_response_maps_fields(adapter):
    candles = adapter._parse_rest_response([candle(), candle("2024-01-01T00:05:00.000Z")])
    assert all(isinstance(c, CandleData) for c in candles)
    assert [c.timestamp for c in candles] == [T0, T0 + 300]
    assert candles[0].to_array()[:6] == [float(T0), 0.85, 0.9, 0.8, 0.88, 1520.5]


def test_parse_rest_response_treats_none_values_as_zero(adapter):
    row = candle(open="None", high=None, low="None", close=None, volume="None")
    (parsed,) = adapter._parse_rest_response([row])
    assert parsed.to_array()[1:6] == [0.0] * 5


def test_parse_rest_response_skips_non_dict_rows(adapter):
    assert len(adapter._parse_rest_response(["junk", candle()])) == 1


def test_parse_rest_response_empty_list_is_no_data(adapter):
    assert adapter._parse_rest_response([]) == []


@pytest.mark.parametrize("bad", [None, {}, "x", {"error": "Invalid pair"}])
def test_parse_rest_response_unparseable_raises(adapter, bad):
    with pytest.raises(ValueError, match="unexpected REST response"):
        adapter._parse_rest_response(bad)


def test_parse_rest_response_row_without_date_raises(adapter):
    row = candle()
    del row["date"]
    with pytest.raises(ValueError, match="Timestamp"):
        adapter._parse_rest_response([row])


def test_ws_subscription_payload(adapter):
    assert adapter.get_ws_subscription_payload(PAIR, "1h") == {
        "pair": "ALOT/USDC",
        "chart": "H1",
        "type": "chart-v2-subscribe",
    }


def test_parse_ws_message_uses_last_candle(adapter):
    message = {"type": "liveCandle", "data": [candle(), candle("2024-01-01T00:05:00.000Z")]}
    (parsed,) = adapter.parse_ws_message(message)
    assert parsed.timestamp == T0 + 300


@pytest.mark.parametrize(
    "message",
    [
        None,
        "x",
        {"type": "chartSnapShot", "data": [candle()]},
        {"type": "liveCandle", "data": []},
        {"type": "liveCandle", "data": "x"},
        {"type": "liveCandle", "data": ["junk"]},
        {"type": "invalid", "data": "some_data"},
    ],
)
def test_parse_ws_message_ignores_non_candle_payloads(adapter, message):
    assert adapter.parse_ws_message(message) is None


async def test_fetch_rest_candles(adapter):
    client = MagicMock()
    client.get_rest_data = AsyncMock(return_value=[candle()])
    candles = await adapter.fetch_rest_candles(
        PAIR, "5m", start_time=T0, limit=10, network_client=client
    )
    assert [c.timestamp for c in candles] == [T0]
    client.get_rest_data.assert_awaited_once_with(
        url=adapter._get_rest_url(), params=adapter._get_rest_params(PAIR, "5m", T0, 10)
    )


async def test_fetch_requires_network_client(adapter):
    with pytest.raises(ValueError, match="network_client"):
        await adapter.fetch_rest_candles(PAIR, "5m")


def test_fetch_synchronously_is_not_supported(adapter):
    with pytest.raises(NotImplementedError):
        adapter.fetch_rest_candles_synchronous(PAIR, "5m")


def test_registry_lookup():
    assert ExchangeRegistry.get_adapter_class("dexalot_spot") is DexalotSpotAdapter
    assert isinstance(
        ExchangeRegistry.get_adapter_instance("dexalot_spot", network_config=None),
        DexalotSpotAdapter,
    )


def test_factory_lookup():
    assert CandlesFactory._CONNECTOR_MAP["dexalot"] == "dexalot_spot"
    built = CandlesFactory.get_candle(CandlesConfig(connector="dexalot", trading_pair=PAIR))
    assert built.name == "dexalot_spot"
