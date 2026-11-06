"""Behaviour tests shared by the sync, async and hybrid mocked adapters."""

import pytest

from candles_feed.core.network_config import NetworkConfig
from candles_feed.mocking_resources.adapter.async_mocked_adapter import AsyncMockedAdapter
from candles_feed.mocking_resources.adapter.constants import (
    DEFAULT_CANDLES_LIMIT,
    INTERVALS,
    REST_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)
from candles_feed.mocking_resources.adapter.hybrid_mocked_adapter import HybridMockedAdapter
from candles_feed.mocking_resources.adapter.sync_mocked_adapter import SyncMockedAdapter

ALL_ADAPTERS = [SyncMockedAdapter, AsyncMockedAdapter, HybridMockedAdapter]
SYNC_ADAPTERS = [SyncMockedAdapter, HybridMockedAdapter]
ASYNC_ADAPTERS = [AsyncMockedAdapter, HybridMockedAdapter]

START = 1_700_000_000


@pytest.fixture(params=ALL_ADAPTERS, ids=lambda cls: cls.__name__)
def adapter(request):
    return request.param()


def ok_response(*items):
    return {"status": "ok", "data": list(items)}


def test_init_keeps_network_config_and_client():
    config = NetworkConfig()
    client = object()
    for cls in ALL_ADAPTERS:
        built = cls(network_config=config, network_client=client)
        assert built._network_config is config
        assert built._network_client is client
        assert cls()._network_client is None


def test_trading_pair_format_is_identity(adapter):
    assert adapter.get_trading_pair_format("BTC-USDT") == "BTC-USDT"


def test_intervals_and_ws_metadata(adapter):
    assert adapter.get_supported_intervals() == INTERVALS
    assert adapter.get_ws_supported_intervals() == list(INTERVALS)
    assert adapter.get_ws_url() == SPOT_WSS_URL
    assert adapter._get_rest_url() == f"{SPOT_REST_URL}{REST_CANDLES_ENDPOINT}"


def test_ws_subscription_payload(adapter):
    assert adapter.get_ws_subscription_payload("BTC-USDT", "1m") == {
        "type": "subscribe",
        "subscriptions": [{"symbol": "BTC-USDT", "interval": "1m"}],
    }


def test_parse_ws_message_converts_ms_timestamp_to_seconds(adapter):
    message = {
        "data": {
            "timestamp": START * 1000,
            "open": "1",
            "high": "2",
            "low": "0.5",
            "close": "1.5",
            "volume": "10",
            "quote_volume": "15",
        }
    }
    (candle,) = adapter.parse_ws_message(message)
    assert candle.timestamp == START
    assert (candle.open, candle.high, candle.low, candle.close) == (1.0, 2.0, 0.5, 1.5)
    assert candle.volume == 10.0
    assert candle.quote_asset_volume == 15.0


def test_parse_ws_message_missing_fields_default_to_zero(adapter):
    (candle,) = adapter.parse_ws_message({"data": {"timestamp": START * 1000}})
    assert candle.open == candle.close == candle.volume == candle.quote_asset_volume == 0.0


@pytest.mark.parametrize("message", [{}, {"data": {}}, {"data": {"open": 1}}])
def test_parse_ws_message_without_timestamp_returns_none(adapter, message):
    assert adapter.parse_ws_message(message) is None


def test_rest_params_minimal(adapter):
    assert adapter._get_rest_params("BTC-USDT", "1m") == {
        "symbol": "BTC-USDT",
        "interval": "1m",
        "limit": DEFAULT_CANDLES_LIMIT,
    }


def test_rest_params_convert_times_to_exchange_milliseconds(adapter):
    params = adapter._get_rest_params(
        "BTC-USDT", "5m", start_time=START, end_time=START + 60, limit=7
    )
    assert params["start_time"] == START * 1000
    assert params["end_time"] == (START + 60) * 1000
    assert params["limit"] == 7


def test_rest_params_zero_start_time_is_kept(adapter):
    assert adapter._get_rest_params("BTC-USDT", "1m", start_time=0)["start_time"] == 0


def test_parse_rest_response_builds_candles(adapter):
    candles = adapter._parse_rest_response(
        ok_response(
            {
                "timestamp": START * 1000,
                "open": 1,
                "high": 2,
                "low": 0,
                "close": 1,
                "volume": 3,
                "quote_volume": 4,
            },
            {"timestamp": (START + 60) * 1000},
        )
    )
    assert [c.timestamp for c in candles] == [START, START + 60]
    assert candles[0].quote_asset_volume == 4.0
    assert candles[1].high == 0.0


def test_parse_rest_response_skips_non_dict_items(adapter):
    response = ok_response("junk", None, {"timestamp": START * 1000})
    assert [c.timestamp for c in adapter._parse_rest_response(response)] == [START]


@pytest.mark.parametrize(
    "response",
    [
        None,
        [],
        {"status": "error", "data": [{"timestamp": START * 1000}]},
        {"status": "ok", "data": "not-a-list"},
        {"status": "ok"},
    ],
)
def test_parse_rest_response_rejects_unusable_payloads(adapter, response):
    assert adapter._parse_rest_response(response) == []


@pytest.mark.parametrize("cls", SYNC_ADAPTERS)
def test_synchronous_fetch_generates_ascending_candles(cls):
    candles = cls().fetch_rest_candles_synchronous("BTC-USDT", "5m", start_time=START, limit=3)
    assert [c.timestamp for c in candles] == [START, START + 300, START + 600]
    assert [c.open for c in candles] == [100.0, 101.0, 102.0]
    assert candles[2].volume == 1020.0
    assert candles[1].quote_asset_volume == 100600.0


@pytest.mark.parametrize("cls", SYNC_ADAPTERS)
def test_synchronous_fetch_defaults(cls):
    adapter = cls()
    default = adapter.fetch_rest_candles_synchronous("BTC-USDT", "1m")
    assert len(default) == 500
    assert default[0].timestamp == 1_620_000_000
    # An unknown interval falls back to one minute spacing; a None limit means 500.
    odd = adapter.fetch_rest_candles_synchronous("BTC-USDT", "nope", start_time=START, limit=None)
    assert len(odd) == 500
    assert odd[1].timestamp - odd[0].timestamp == 60


@pytest.mark.parametrize("cls", ASYNC_ADAPTERS)
async def test_async_fetch_generates_candles(cls):
    candles = await cls().fetch_rest_candles("BTC-USDT", "1h", start_time=START, limit=2)
    assert [c.timestamp for c in candles] == [START, START + 3600]
    first_open = 100.0 if cls is AsyncMockedAdapter else 200.0
    step = 1.0 if cls is AsyncMockedAdapter else 2.0
    assert [c.open for c in candles] == [first_open, first_open + step]


@pytest.mark.parametrize("cls", ASYNC_ADAPTERS)
async def test_async_fetch_accepts_clients_and_defaults(cls):
    sentinel = object()
    default = await cls(network_client=sentinel).fetch_rest_candles("BTC-USDT", "1m")
    assert len(default) == 500
    assert default[0].timestamp == 1_620_000_000
    explicit = await cls().fetch_rest_candles(
        "BTC-USDT", "nope", start_time=START, limit=None, network_client=sentinel
    )
    assert len(explicit) == 500
    assert explicit[1].timestamp - explicit[0].timestamp == 60


async def test_hybrid_sync_and_async_paths_differ():
    adapter = HybridMockedAdapter()
    sync_candles = adapter.fetch_rest_candles_synchronous(
        "BTC-USDT", "1m", start_time=START, limit=1
    )
    async_candles = await adapter.fetch_rest_candles("BTC-USDT", "1m", start_time=START, limit=1)
    assert sync_candles[0].timestamp == async_candles[0].timestamp
    assert sync_candles[0].open == 100.0
    assert async_candles[0].open == 200.0
