"""Behaviour tests for HyperliquidBasePlugin handlers and formatters (called directly)."""

import asyncio
import json
from unittest.mock import Mock

import pytest
from aiohttp.streams import StreamReader
from aiohttp.test_utils import make_mocked_request

from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.exchange_server_plugins.hyperliquid.base_plugin import (
    HyperliquidBasePlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.hyperliquid.perpetual_plugin import (
    HyperliquidPerpetualPlugin,
)
from candles_feed.mocking_resources.exchange_server_plugins.hyperliquid.spot_plugin import (
    HyperliquidSpotPlugin,
)


class FakeServer:
    """Minimal stand-in for the mock exchange server used by the plugin handlers."""

    def __init__(self, trading_pairs=("BTC-USDT", "ETH-USDC"), allow=True):
        self.trading_pairs = list(trading_pairs)
        self.allow = allow
        self.simulated = 0

    async def _simulate_network_conditions(self):
        self.simulated += 1

    def _check_rate_limit(self, client_ip, kind):
        return self.allow


@pytest.fixture
def plugin():
    return HyperliquidSpotPlugin()


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


def post_request(raw: bytes):
    """A POST request whose body is ``raw``."""
    payload = StreamReader(Mock(_reading_paused=False), 2**16, loop=asyncio.get_running_loop())
    payload.feed_data(raw)
    payload.feed_eof()
    return make_mocked_request(
        "POST", "/info", headers={"Content-Length": str(len(raw))}, payload=payload
    )


def test_urls_and_routes_come_from_adapter_constants(plugin):
    assert HyperliquidBasePlugin.rest_url.fget(plugin).startswith("https://")
    assert HyperliquidBasePlugin.wss_url.fget(plugin).startswith("wss://")
    assert HyperliquidBasePlugin.ws_routes.fget(plugin) == {"/ws": "handle_websocket"}


def test_format_rest_candles_numeric_rows(plugin, candle):
    out = HyperliquidBasePlugin.format_rest_candles(plugin, [candle], "BTC-USDT", "1m")
    assert out == [[1_700_000_000, 100.0, 110.0, 90.0, 105.0, 10.0, 1000.0]]
    assert HyperliquidBasePlugin.format_rest_candles(plugin, [], "BTC-USDT", "1m") == []


def test_format_ws_candle_message(plugin, candle):
    msg = HyperliquidBasePlugin.format_ws_candle_message(plugin, candle, "BTC-USDT", "1h")
    assert msg == {
        "channel": "candles",
        "coin": "BTC",
        "interval": "60",
        "data": [1_700_000_000, 100.0, 110.0, 90.0, 105.0, 10.0, 1000.0],
    }


def test_format_ws_candle_message_unknown_interval_passthrough(plugin, candle):
    msg = HyperliquidBasePlugin.format_ws_candle_message(plugin, candle, "ETH-USDT", "7z")
    assert msg["interval"] == "7z"
    assert msg["coin"] == "ETH"


def test_parse_ws_subscription_maps_coin_and_interval(plugin):
    message = {"method": "subscribe", "channel": "candles", "coin": "ETH", "interval": "D"}
    assert HyperliquidBasePlugin.parse_ws_subscription(plugin, message) == [("ETH-USDT", "1d")]


def test_parse_ws_subscription_unknown_interval_kept(plugin):
    message = {"method": "subscribe", "channel": "candles", "coin": "ETH", "interval": "zz"}
    assert HyperliquidBasePlugin.parse_ws_subscription(plugin, message) == [("ETH-USDT", "zz")]


@pytest.mark.parametrize(
    "message",
    [
        {"method": "unsubscribe", "channel": "candles", "coin": "BTC", "interval": "1"},
        {"method": "subscribe", "channel": "trades", "coin": "BTC", "interval": "1"},
        {"method": "subscribe", "channel": "candles", "interval": "1"},
        {"method": "subscribe", "channel": "candles", "coin": "BTC"},
    ],
)
def test_parse_ws_subscription_ignores_incomplete_messages(plugin, message):
    assert HyperliquidBasePlugin.parse_ws_subscription(plugin, message) == []


def test_subscription_success_and_key(plugin):
    ok = HyperliquidBasePlugin.create_ws_subscription_success(plugin, {}, [])
    assert ok == {"success": True, "message": "Subscription successful"}
    assert HyperliquidBasePlugin.create_ws_subscription_key(plugin, "BTC-USDT", "1h") == "BTC:60"
    assert HyperliquidBasePlugin.create_ws_subscription_key(plugin, "BTC-USDT", "9z") == "BTC:9z"


async def test_parse_rest_params_from_json_body(plugin):
    body = {"coin": "BTC", "resolution": "60", "startTime": 1, "endTime": 2, "limit": 3}
    params = await HyperliquidBasePlugin.parse_rest_candles_params(
        plugin, post_request(json.dumps(body).encode())
    )
    assert params == {
        "symbol": "BTC-USDT",
        "interval": "1h",
        "start_time": 1,
        "end_time": 2,
        "limit": 3,
    }


async def test_parse_rest_params_unknown_resolution_kept(plugin):
    raw = json.dumps({"coin": "BTC", "resolution": "zz"}).encode()
    params = await HyperliquidBasePlugin.parse_rest_candles_params(plugin, post_request(raw))
    assert params["interval"] == "zz"
    assert params["start_time"] is None


@pytest.mark.parametrize("raw", [b"not json", b'{"coin": "BTC"}', b'{"resolution": "1"}', b"{}"])
async def test_parse_rest_params_invalid_or_incomplete_body_is_empty(plugin, raw):
    assert await HyperliquidBasePlugin.parse_rest_candles_params(plugin, post_request(raw)) == {}


@pytest.mark.parametrize(
    ("plugin_cls", "kind"),
    [(HyperliquidSpotPlugin, "spot"), (HyperliquidPerpetualPlugin, "perpetual")],
)
async def test_handle_instruments_reports_market_type(plugin_cls, kind):
    server = FakeServer()
    response = await HyperliquidBasePlugin.handle_instruments(
        plugin_cls(), server, make_mocked_request("GET", "/i")
    )
    items = json.loads(response.text)
    assert [(i["coin"], i["quoteCurrency"], i["type"]) for i in items] == [
        ("BTC", "USDT", kind),
        ("ETH", "USDC", kind),
    ]
    assert server.simulated == 1


async def test_handle_instruments_rate_limited(plugin):
    response = await HyperliquidBasePlugin.handle_instruments(
        plugin, FakeServer(allow=False), make_mocked_request("GET", "/i")
    )
    assert response.status == 429
    assert json.loads(response.text) == {"error": "Rate limit exceeded"}


@pytest.mark.parametrize(
    ("interval", "seconds"),
    [("15s", 15), ("5m", 300), ("2h", 7200), ("1d", 86400), ("1w", 604800)],
)
def test_interval_to_seconds(interval, seconds):
    assert HyperliquidBasePlugin._interval_to_seconds(interval) == seconds


def test_interval_to_seconds_unknown_unit_raises():
    with pytest.raises(ValueError, match="Unknown interval unit: q"):
        HyperliquidBasePlugin._interval_to_seconds("3q")
