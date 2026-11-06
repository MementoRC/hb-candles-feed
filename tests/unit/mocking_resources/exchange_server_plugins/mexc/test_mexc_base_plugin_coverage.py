"""Behaviour tests for MEXCBasePlugin handlers and formatters (called directly)."""

import json

import pytest
from aiohttp.test_utils import make_mocked_request

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.exchange_server_plugins.mexc.base_plugin import MEXCBasePlugin
from candles_feed.mocking_resources.exchange_server_plugins.mexc.spot_plugin import MEXCSpotPlugin


class FakeServer:
    """Minimal stand-in for the mock exchange server used by the plugin handlers."""

    def __init__(self, trading_pairs=("BTC-USDT", "ETH-BTC"), allow=True):
        self.trading_pairs = list(trading_pairs)
        self.allow = allow
        self.simulated = 0
        self.rate_checks = []

    async def _simulate_network_conditions(self):
        self.simulated += 1

    def _check_rate_limit(self, client_ip, kind):
        self.rate_checks.append((client_ip, kind))
        return self.allow


@pytest.fixture
def plugin():
    return MEXCSpotPlugin()


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
    assert MEXCBasePlugin.rest_url.fget(plugin).startswith("https://")
    assert MEXCBasePlugin.wss_url.fget(plugin).startswith("wss://")
    assert MEXCBasePlugin.ws_routes.fget(plugin) == {"/ws": "handle_websocket"}


def test_format_rest_candles_row_layout(plugin, candle):
    (row,) = MEXCBasePlugin.format_rest_candles(plugin, [candle], "BTC-USDT", "1m")
    assert row[0] == candle.timestamp_ms
    assert row[1:6] == ["100.0", "110.0", "90.0", "105.0", "10.0"]
    assert row[6] == candle.timestamp_ms + 60_000
    assert row[7] == "1000.0"
    assert row[9] == str(10.0 * 0.7)
    assert row[10] == str(1000.0 * 0.7)


@pytest.mark.parametrize(
    ("interval", "millis"),
    [
        ("2m", 120_000),
        ("1h", 3_600_000),
        ("1d", 86_400_000),
        ("1w", 604_800_000),
        ("1M", 2_592_000_000),
        ("1x", 60_000),
    ],
)
def test_interval_to_milliseconds(plugin, interval, millis):
    assert MEXCBasePlugin._interval_to_milliseconds(plugin, interval) == millis


def test_format_ws_candle_message_maps_fields(plugin, candle):
    msg = MEXCBasePlugin.format_ws_candle_message(plugin, candle, "BTC-USDT", "1h", is_final=True)
    assert msg["e"] == "push.kline"
    assert msg["d"] == {
        "s": "BTC_USDT",
        "c": "105.0",
        "h": "110.0",
        "l": "90.0",
        "o": "100.0",
        "v": "10.0",
        "qv": "1000.0",
        "t": candle.timestamp_ms,
        "i": "Min60",
        "n": 100,
        "x": True,
    }


def test_format_ws_candle_message_unknown_interval_passthrough(plugin, candle):
    msg = MEXCBasePlugin.format_ws_candle_message(plugin, candle, "BTC-USDT", "7z")
    assert msg["d"]["i"] == "7z"
    assert msg["d"]["x"] is False


def test_parse_ws_subscription_contract_topic(plugin):
    message = {
        "method": "sub",
        "params": ["contract@kline.Min1_btcusdt", "contract@kline.Hour4_ethbtc"],
    }
    assert MEXCBasePlugin.parse_ws_subscription(plugin, message) == [
        ("BTC-USDT", "1m"),
        ("ETH-BTC", "4h"),
    ]


def test_parse_ws_subscription_spot_topic(plugin):
    message = {
        "method": "sub",
        "params": ["spot@public.kline.Min1_btcusdt", "spot@public.kline.Hour4_ethbtc"],
    }
    assert MEXCBasePlugin.parse_ws_subscription(plugin, message) == [
        ("BTC-USDT", "1m"),
        ("ETH-BTC", "4h"),
    ]


def test_parse_ws_subscription_unsub_parses_like_sub(plugin):
    message = {"method": "unsub", "params": ["spot@public.kline.Min1_btcusdt"]}
    assert MEXCBasePlugin.parse_ws_subscription(plugin, message) == [("BTC-USDT", "1m")]


def test_parse_ws_subscription_keeps_unknown_interval_and_unsplittable_symbol(plugin):
    message = {"method": "sub", "params": ["contract@kline.Bogus_abcdef"]}
    assert MEXCBasePlugin.parse_ws_subscription(plugin, message) == [("ABCDEF", "Bogus")]


def test_parse_ws_subscription_ignores_other_methods_and_malformed_topics(plugin):
    assert (
        MEXCBasePlugin.parse_ws_subscription(
            plugin, {"method": "other", "params": ["spot@public.kline.Min1_btcusdt"]}
        )
        == []
    )
    params = ["spot@trades.btcusdt", "a@b@kline.Min1_btcusdt", "x@kline.Min1", "x@kline."]
    message = {"method": "sub", "params": params}
    assert MEXCBasePlugin.parse_ws_subscription(plugin, message) == []


def test_subscription_success_depends_on_subscriptions(plugin):
    ok = MEXCBasePlugin.create_ws_subscription_success(plugin, {}, [("BTC-USDT", "1m")])
    assert ok["channel"] == "sub.response"
    assert ok["data"] == {"success": True}
    failed = MEXCBasePlugin.create_ws_subscription_success(plugin, {}, [])
    assert failed["data"] == {"success": False, "message": "No valid subscriptions"}


def test_subscription_key(plugin):
    assert MEXCBasePlugin.create_ws_subscription_key(plugin, "BTC-USDT", "1m") == "BTC_USDT@Min1"
    assert MEXCBasePlugin.create_ws_subscription_key(plugin, "BTC-USDT", "9z") == "BTC_USDT@9z"


def test_parse_rest_params_maps_names(plugin):
    request = make_mocked_request(
        "GET", "/k?symbol=BTCUSDT&interval=Min1&startTime=10&endTime=20&limit=50"
    )
    params = MEXCBasePlugin.parse_rest_candles_params(plugin, request)
    assert params == {
        "symbol": "BTCUSDT",
        "interval": "Min1",
        "start_time": "10",
        "end_time": "20",
        "limit": 50,
        "startTime": "10",
        "endTime": "20",
    }


def test_parse_rest_params_invalid_limit_falls_back(plugin):
    request = make_mocked_request("GET", "/k?symbol=BTCUSDT&limit=lots")
    assert MEXCBasePlugin.parse_rest_candles_params(plugin, request)["limit"] == 500


def test_parse_rest_params_without_limit(plugin):
    request = make_mocked_request("GET", "/k?symbol=BTCUSDT")
    assert MEXCBasePlugin.parse_rest_candles_params(plugin, request)["limit"] is None


async def test_handle_instruments_lists_trading_pairs(plugin):
    server = FakeServer()
    response = await MEXCBasePlugin.handle_instruments(
        plugin, server, make_mocked_request("GET", "/i")
    )
    data = json.loads(response.text)
    assert response.status == 200
    assert data["code"] == 0
    assert [(i["symbol"], i["baseAsset"], i["quoteAsset"]) for i in data["data"]] == [
        ("BTC_USDT", "BTC", "USDT"),
        ("ETH_BTC", "ETH", "BTC"),
    ]
    assert server.simulated == 1
    assert server.rate_checks[0][1] == "rest"


async def test_handle_instruments_rate_limited(plugin):
    response = await MEXCBasePlugin.handle_instruments(
        plugin, FakeServer(allow=False), make_mocked_request("GET", "/i")
    )
    assert response.status == 429
    assert json.loads(response.text) == {"error": "Rate limit exceeded"}
