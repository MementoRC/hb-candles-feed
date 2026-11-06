"""
Behavioural coverage tests for the ExchangePlugin base class defaults.
"""

import time

import pytest

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class DefaultPlugin(ExchangePlugin):
    """Concrete plugin whose abstract members defer to the base-class bodies."""

    @property
    def rest_routes(self):
        return super().rest_routes

    @property
    def ws_routes(self):
        return super().ws_routes

    def format_rest_candles(self, candles, trading_pair, interval):
        return super().format_rest_candles(candles, trading_pair, interval)

    def format_ws_candle_message(self, candle, trading_pair, interval, is_final=False):
        return super().format_ws_candle_message(candle, trading_pair, interval, is_final)

    def parse_ws_subscription(self, message):
        return super().parse_ws_subscription(message)

    def create_ws_subscription_success(self, message, subscriptions):
        return super().create_ws_subscription_success(message, subscriptions)

    def create_ws_subscription_key(self, trading_pair, interval):
        return super().create_ws_subscription_key(trading_pair, interval)

    def parse_rest_candles_params(self, request):
        return super().parse_rest_candles_params(request)


@pytest.fixture
def plugin():
    return DefaultPlugin(ExchangeType.BINANCE_SPOT, BinanceSpotAdapter)


def test_cannot_instantiate_abstract_base():
    with pytest.raises(TypeError, match="abstract"):
        ExchangePlugin(ExchangeType.BINANCE_SPOT, BinanceSpotAdapter)  # type: ignore[abstract]


def test_constructor_stores_type_and_adapter(plugin):
    assert plugin.exchange_type is ExchangeType.BINANCE_SPOT
    assert plugin.adapter_class is BinanceSpotAdapter


def test_default_rate_limits(plugin):
    limits = plugin.rate_limits
    assert limits["rest"] == {"limit": 100, "period_ms": 60000, "weights": {}}
    assert limits["ws"] == {
        "limit": 10,
        "burst": 20,
        "connection_limit": 50,
        "subscription_limit": 1000,
    }


def test_rate_limits_are_fresh_per_access(plugin):
    plugin.rate_limits["rest"]["limit"] = 1
    assert plugin.rate_limits["rest"]["limit"] == 100


def test_default_api_key(plugin):
    key = plugin.api_keys["test_key"]
    assert key["permissions"] == ["READ", "TRADE"]
    assert key["ip_whitelist"] == ["*"]
    assert key["enabled"] is True
    assert key["api_secret"]
    age_ms = int(time.time() * 1000) - key["created_time"]
    assert 86_000_000 < age_ms < 87_000_000


def test_default_network_settings(plugin):
    assert plugin.network_settings == {
        "websocket_keep_alive": {"interval_seconds": 30, "type": "ping"}
    }


def test_normalize_trading_pair_uppercases(plugin):
    assert plugin.normalize_trading_pair("btc-usdt") == "BTC-USDT"


@pytest.mark.parametrize("to_exchange", [True, False])
def test_translate_interval_is_identity(plugin, to_exchange):
    assert plugin.translate_interval("5m", to_exchange=to_exchange) == "5m"


def test_default_urls_are_empty(plugin):
    assert plugin.rest_url == ""
    assert plugin.wss_url == ""
    assert plugin.urls == {"rest": "", "ws": ""}


def test_get_patched_urls(plugin):
    assert plugin.get_patched_urls("localhost", 8123) == {
        "rest": "http://localhost:8123",
        "ws": "ws://localhost:8123/ws",
    }


def test_abstract_members_default_to_none(plugin):
    assert plugin.rest_routes is None
    assert plugin.ws_routes is None
    assert plugin.format_rest_candles([], "BTC-USDT", "1m") is None
    assert plugin.format_ws_candle_message(None, "BTC-USDT", "1m") is None
    assert plugin.parse_ws_subscription({}) is None
    assert plugin.create_ws_subscription_success({}, []) is None
    assert plugin.create_ws_subscription_key("BTC-USDT", "1m") is None
    assert plugin.parse_rest_candles_params(None) is None
