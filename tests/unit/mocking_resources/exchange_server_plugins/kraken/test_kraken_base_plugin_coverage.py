"""Behaviour tests for KrakenBasePlugin helpers, formatters and handlers (called directly)."""

import json

import pytest
from aiohttp.test_utils import make_mocked_request

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.exchange_server_plugins.kraken.base_plugin import (
    KrakenBasePlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.kraken.spot_plugin import (
    KrakenSpotPlugin,
)


class FakeServer:
    """Minimal stand-in for the mock exchange server used by the plugin handlers."""

    def __init__(self, allow=True, now=1_700_000_000.5):
        self.allow = allow
        self.now = now
        self.simulated = 0

    async def _simulate_network_conditions(self):
        self.simulated += 1

    def _check_rate_limit(self, client_ip, kind):
        return self.allow

    def _time(self):
        return self.now


@pytest.fixture
def plugin():
    return KrakenSpotPlugin()


@pytest.fixture
def candle():
    return CandleData(
        timestamp_raw=1_700_000_000,
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=10.0,
        quote_asset_volume=1000.0,
    )


def test_urls_and_routes_come_from_adapter_constants(plugin):
    assert KrakenBasePlugin.rest_url.fget(plugin).startswith("https://")
    assert KrakenBasePlugin.wss_url.fget(plugin).startswith("wss://")
    assert KrakenBasePlugin.ws_routes.fget(plugin) == {"/ws": "handle_websocket"}


@pytest.mark.parametrize(
    ("standard", "kraken"),
    [("BTC-USDT", "XBT/USD"), ("ETH-USD", "ETH/USD"), ("BTCUSDT", "BTCUSDT"), ("", "")],
)
def test_format_trading_pair(plugin, standard, kraken):
    assert KrakenBasePlugin._format_trading_pair(plugin, standard) == kraken


@pytest.mark.parametrize(
    ("kraken", "standard"),
    [
        ("XBT/USD", "BTC-USDT"),
        ("ETH/EUR", "ETH-EUR"),
        ("XXBTZUSD", "BTC-USDT"),
        ("XETHZUSD", "ETH-USDT"),
        ("ABCDEF", "ABC-DEF"),
        ("AB", "AB"),
        ("", ""),
    ],
)
def test_reverse_format_trading_pair(plugin, kraken, standard):
    assert KrakenBasePlugin._reverse_format_trading_pair(plugin, kraken) == standard


def test_interval_to_seconds_defaults_to_one_minute(plugin):
    assert KrakenBasePlugin._interval_to_seconds(plugin, "1h") == 3600
    assert KrakenBasePlugin._interval_to_seconds(plugin, "bogus") == 60


def test_format_rest_candles_rows_and_last(plugin, candle):
    out = KrakenBasePlugin.format_rest_candles(plugin, [candle], "BTC-USDT", "1m")
    assert out["error"] == []
    assert out["result"]["last"] == 1_700_000_000
    assert out["result"]["XBT/USD"] == [
        [1_700_000_000, "100.0", "110.0", "90.0", "105.0", str(105.0 * 0.9999), "10.0", 100]
    ]


def test_format_rest_candles_empty_last_is_zero(plugin):
    out = KrakenBasePlugin.format_rest_candles(plugin, [], "BTC-USDT", "1m")
    assert out["result"] == {"XBT/USD": [], "last": 0}


def test_format_ws_candle_message_layout(plugin, candle):
    channel_id, data, channel, pair = KrakenBasePlugin.format_ws_candle_message(
        plugin, candle, "BTC-USDT", "5m"
    )
    assert channel_id == 0
    assert channel == "ohlc-5"
    assert pair == "XBT/USD"
    assert data[0] == "1700000000.000000"
    assert data[1] == "1700000300.000000"
    assert data[2:6] == ["100.00000", "110.00000", "90.00000", "105.00000"]
    assert data[6] == f"{105.0 * 0.9999:.5f}"
    assert data[7] == "10.00000000"


def test_format_ws_candle_message_unknown_interval_defaults(plugin, candle):
    msg = KrakenBasePlugin.format_ws_candle_message(plugin, candle, "BTC-USDT", "7z")
    assert msg[2] == "ohlc-1"
    assert msg[1][1] == "1700000060.000000"


def test_parse_ws_subscription_pairs_and_interval(plugin):
    message = {
        "name": "subscribe",
        "pair": ["XBT/USD", "ETH/EUR"],
        "subscription": {"name": "ohlc", "interval": 5},
    }
    assert KrakenBasePlugin.parse_ws_subscription(plugin, message) == [
        ("BTC-USDT", "5m"),
        ("ETH-EUR", "5m"),
    ]


def test_parse_ws_subscription_unknown_interval_defaults_to_1m(plugin):
    message = {
        "name": "subscribe",
        "pair": ["ETH/EUR"],
        "subscription": {"name": "ohlc", "interval": 99},
    }
    assert KrakenBasePlugin.parse_ws_subscription(plugin, message) == [("ETH-EUR", "1m")]


@pytest.mark.parametrize(
    "message",
    [
        {"name": "unsubscribe"},
        {"name": "subscribe", "pair": ["XBT/USD"], "subscription": {"name": "trade"}},
        {"name": "subscribe", "pair": ["XBT/USD"]},
        ["not", "a", "dict"],
    ],
)
def test_parse_ws_subscription_ignores_non_ohlc(plugin, message):
    assert KrakenBasePlugin.parse_ws_subscription(plugin, message) == []


def test_subscription_success_describes_first_subscription(plugin):
    out = KrakenBasePlugin.create_ws_subscription_success(
        plugin, {"reqid": 7}, [("BTC-USDT", "5m"), ("ETH-EUR", "1m")]
    )
    assert out["status"] == "subscribed"
    assert out["reqid"] == 7
    assert out["pair"] == "XBT/USD"
    assert out["channelName"] == "ohlc-5"
    assert out["subscription"] == {"interval": 5, "name": "ohlc"}
    assert 0 <= out["channelID"] < 1000


def test_subscription_success_without_subscriptions_is_error(plugin):
    out = KrakenBasePlugin.create_ws_subscription_success(plugin, {}, [])
    assert out == {"errorMessage": "No valid subscriptions found", "status": "error", "reqid": 1}


def test_subscription_key(plugin):
    assert KrakenBasePlugin.create_ws_subscription_key(plugin, "BTC-USDT", "1h") == (
        "ohlc-60_XBT/USD"
    )
    assert KrakenBasePlugin.create_ws_subscription_key(plugin, "BTC-USDT", "9z") == (
        "ohlc-1_XBT/USD"
    )


def test_parse_rest_params_full(plugin):
    request = make_mocked_request("GET", "/OHLC?pair=XBT/USD&interval=15&since=1234")
    assert KrakenBasePlugin.parse_rest_candles_params(plugin, request) == {
        "symbol": "BTC-USDT",
        "interval": "15m",
        "limit": 720,
        "start_time": 1234,
    }


def test_parse_rest_params_defaults_and_bad_since(plugin):
    request = make_mocked_request("GET", "/OHLC?interval=999&since=abc")
    params = KrakenBasePlugin.parse_rest_candles_params(plugin, request)
    assert params == {"symbol": None, "interval": "1m", "limit": 720}


async def test_handle_time_returns_unixtime(plugin):
    server = FakeServer()
    response = await KrakenBasePlugin.handle_time(plugin, server, make_mocked_request("GET", "/t"))
    data = json.loads(response.text)
    assert response.status == 200
    assert data["error"] == []
    assert data["result"]["unixtime"] == 1_700_000_000
    assert server.simulated == 1


async def test_handle_time_rate_limited(plugin):
    response = await KrakenBasePlugin.handle_time(
        plugin, FakeServer(allow=False), make_mocked_request("GET", "/t")
    )
    assert response.status == 429
    assert json.loads(response.text) == {"error": ["EAPI:Rate limit exceeded"]}
