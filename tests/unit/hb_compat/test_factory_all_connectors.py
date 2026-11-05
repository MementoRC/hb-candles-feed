"""Real (unmocked) construction of every CandlesFactory connector-map entry (#94).

The sibling tests mock ExchangeRegistry, which hides adapters whose constructors
do not accept ``network_config``. Nothing here mocks the factory, registry or
adapter constructors; network access is forbidden instead.
"""

import socket

import aiohttp
import pytest

import candles_feed  # noqa: F401  (triggers adapter discovery)
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.adapter import CandlesBaseAdapter
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory

_CONNECTORS = sorted(CandlesFactory._CONNECTOR_MAP)
_REGISTERED = sorted(
    name
    for name in ExchangeRegistry.get_registered_exchanges()
    if "mock" not in name and not name.startswith("test")
)


@pytest.fixture(autouse=True)
def mock_exchange_registry():
    """Override the conftest fixture: use the real registry."""
    yield None


@pytest.fixture(autouse=True)
def mock_network_client_factory():
    """Override the conftest fixture: use the real network client factory."""
    yield None


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def _blocked(*_args, **_kwargs):
        raise AssertionError("network access attempted during construction")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(aiohttp.ClientSession, "_request", _blocked)


def test_connector_map_is_not_empty():
    assert _CONNECTORS
    assert _REGISTERED


@pytest.mark.parametrize("connector", _CONNECTORS, ids=_CONNECTORS)
def test_get_candle_constructs_every_connector(connector):
    config = CandlesConfig(
        connector=connector, trading_pair="BTC-USDT", interval="1m", max_records=5
    )

    candle = CandlesFactory.get_candle(config)

    assert isinstance(candle, CandlesBaseAdapter)
    registry_key = CandlesFactory._CONNECTOR_MAP[connector]
    expected_cls = ExchangeRegistry.get_adapter_class(registry_key)
    assert isinstance(candle._feed._adapter, expected_cls)


@pytest.mark.parametrize("exchange", _REGISTERED, ids=_REGISTERED)
def test_candles_feed_constructs_every_registered_adapter(exchange):
    feed = CandlesFeed(exchange=exchange, trading_pair="BTC-USDT", interval="1m", max_records=5)

    assert isinstance(feed._adapter, ExchangeRegistry.get_adapter_class(exchange))
