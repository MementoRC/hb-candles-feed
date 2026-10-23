"""Tests for the BTCMarketsSpotAdapter (offline, fixture based).

BTC Markets is REST-only, so the shared BaseAdapterTest contract does not apply.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.btc_markets.constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
)
from candles_feed.adapters.btc_markets.spot_adapter import BTCMarketsSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory

T0 = 1704067200  # 2024-01-01T00:00:00Z
PAIR = "BTC-AUD"

# Shaped like GET /v3/markets/{marketId}/candles: [time, open, high, low, close, volume].
CANDLES_RESPONSE = [
    ["2024-01-01T00:01:00.000000Z", "64010.5", "64100.0", "63990.0", "64050.0", "0.5"],
    ["2024-01-01T00:00:00.000000Z", "64000.0", "64020.0", "63950.0", "64010.5", "1.25"],
]


@pytest.fixture
def adapter() -> BTCMarketsSpotAdapter:
    return BTCMarketsSpotAdapter()


def test_pair_is_passed_through_unchanged():
    assert BTCMarketsSpotAdapter.get_trading_pair_format(PAIR) == "BTC-AUD"


def test_rest_url_is_base_and_pair_url_embeds_market_id(adapter):
    assert adapter._get_rest_url() == REST_URL
    assert adapter._get_rest_url_for_pair(PAIR) == f"{REST_URL}/v3/markets/BTC-AUD/candles"


def test_supported_intervals_include_common_set(adapter):
    intervals = adapter.get_supported_intervals()
    assert intervals == INTERVALS
    assert {"1m", "5m", "15m", "1h", "4h", "1d", "1w"} <= set(intervals)
    assert intervals["3h"] == 10800


def test_rest_params_without_start_time(adapter):
    assert adapter._get_rest_params(PAIR, "1h") == {
        "timeWindow": "1h",
        "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    }


def test_rest_params_with_start_time_and_limit(adapter):
    params = adapter._get_rest_params(PAIR, "5m", start_time=T0, limit=50)
    assert params == {"timeWindow": "5m", "limit": 50, "from": "2024-01-01T00:00:00Z"}
    assert "marketId" not in params and "symbol" not in params


def test_max_candles_per_request():
    assert BTCMarketsSpotAdapter.MAX_CANDLES_PER_REQUEST == 1000


def test_parse_rest_response_maps_rows(adapter):
    candles = adapter._parse_rest_response(CANDLES_RESPONSE)
    assert all(isinstance(c, CandleData) for c in candles)
    assert [c.timestamp for c in candles] == [T0 + 60, T0]
    assert candles[1].to_array()[:6] == [float(T0), 64000.0, 64020.0, 63950.0, 64010.5, 1.25]


def test_parse_rest_response_skips_short_and_non_list_rows(adapter):
    assert (
        len(
            adapter._parse_rest_response([["2024-01-01T00:00:00Z", "1"], "junk", *CANDLES_RESPONSE])
        )
        == 2
    )


def test_parse_rest_response_empty_list_is_no_data(adapter):
    assert adapter._parse_rest_response([]) == []


@pytest.mark.parametrize(
    "bad", [None, {}, "x", {"code": "MarketNotFound", "message": "market does not exist"}]
)
def test_parse_rest_response_unparseable_raises(adapter, bad):
    with pytest.raises(ValueError, match="unexpected REST response"):
        adapter._parse_rest_response(bad)


def test_websocket_is_not_supported(adapter):
    assert adapter.get_ws_supported_intervals() == []
    for call in (
        adapter.get_ws_url,
        lambda: adapter.get_ws_subscription_payload(PAIR, "1m"),
        lambda: adapter.parse_ws_message({}),
    ):
        with pytest.raises(NotImplementedError):
            call()


async def test_fetch_requests_pair_specific_url(adapter):
    client = MagicMock()
    client.get_rest_data = AsyncMock(return_value=CANDLES_RESPONSE)
    candles = await adapter.fetch_rest_candles(
        PAIR, "1m", start_time=T0, limit=2, network_client=client
    )
    assert [c.timestamp for c in candles] == [T0 + 60, T0]
    client.get_rest_data.assert_awaited_once_with(
        url=f"{REST_URL}/v3/markets/BTC-AUD/candles",
        params={"timeWindow": "1m", "limit": 2, "from": "2024-01-01T00:00:00Z"},
    )


async def test_fetch_propagates_bad_payload_instead_of_returning_empty(adapter):
    client = MagicMock()
    client.get_rest_data = AsyncMock(return_value={"code": "MarketNotFound"})
    with pytest.raises(ValueError, match="unexpected REST response"):
        await adapter.fetch_rest_candles(PAIR, "1m", network_client=client)


async def test_fetch_requires_network_client(adapter):
    with pytest.raises(ValueError, match="network_client"):
        await adapter.fetch_rest_candles(PAIR, "1m")


def test_fetch_synchronously_is_not_supported(adapter):
    with pytest.raises(NotImplementedError):
        adapter.fetch_rest_candles_synchronous(PAIR, "1m")


def test_registry_lookup():
    assert ExchangeRegistry.get_adapter_class("btc_markets_spot") is BTCMarketsSpotAdapter
    assert isinstance(
        ExchangeRegistry.get_adapter_instance("btc_markets_spot", network_config=None),
        BTCMarketsSpotAdapter,
    )


def test_factory_lookup():
    assert CandlesFactory._CONNECTOR_MAP["btc_markets"] == "btc_markets_spot"
    built = CandlesFactory.get_candle(CandlesConfig(connector="btc_markets", trading_pair=PAIR))
    assert built.name == "btc_markets_spot"
