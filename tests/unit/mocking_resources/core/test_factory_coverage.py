"""
Behavioural coverage tests for the mock server factory.
"""

import sys
import types
from dataclasses import dataclass

import pytest

from candles_feed.mocking_resources.core import factory as factory_module
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin import MockedPlugin

PLUGIN_PKG = "candles_feed.mocking_resources.exchange_server_plugins"


@dataclass(frozen=True)
class FakeExchangeType:
    """Hashable stand-in for an ExchangeType member missing from the plugin mapping."""

    value: str


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    registry: dict = {}
    monkeypatch.setattr(factory_module, "_PLUGIN_REGISTRY", registry)
    return registry


class TestRegisterPlugin:
    def test_registered_plugin_is_returned_without_import(self, isolated_registry):
        plugin = object()
        factory_module.register_plugin(ExchangeType.MOCK, plugin)
        assert isolated_registry == {ExchangeType.MOCK: plugin}
        assert factory_module.get_plugin(ExchangeType.MOCK) is plugin

    def test_duplicate_registration_rejected(self):
        factory_module.register_plugin(ExchangeType.MOCK, object())
        with pytest.raises(ValueError, match="already registered.*mock"):
            factory_module.register_plugin(ExchangeType.MOCK, object())


class TestMappedPlugins:
    def test_mapped_type_is_imported_instantiated_and_cached(self, isolated_registry):
        plugin = factory_module.get_plugin(ExchangeType.MOCK)
        assert isinstance(plugin, MockedPlugin)
        assert isolated_registry[ExchangeType.MOCK] is plugin
        assert factory_module.get_plugin(ExchangeType.MOCK) is plugin

    def test_missing_class_in_mapped_module_returns_none(self, monkeypatch, isolated_registry):
        monkeypatch.setattr(
            factory_module.importlib, "import_module", lambda name: types.ModuleType(name)
        )
        assert factory_module.get_plugin(ExchangeType.MOCK) is None
        assert ExchangeType.MOCK not in isolated_registry


class TestDynamicPluginLookup:
    """Exchange types missing from the mapping are resolved by naming convention."""

    fake_type = FakeExchangeType("fake_thing")
    module_name = f"{PLUGIN_PKG}.fake.thing_plugin"

    def test_conventional_module_is_loaded_and_registered(self, monkeypatch, isolated_registry):
        class FakeThingPlugin:
            pass

        module = types.ModuleType(self.module_name)
        module.FakeThingPlugin = FakeThingPlugin
        monkeypatch.setitem(sys.modules, self.module_name, module)

        plugin = factory_module.get_plugin(self.fake_type)

        assert isinstance(plugin, FakeThingPlugin)
        assert isolated_registry[self.fake_type] is plugin

    def test_missing_module_returns_none(self, isolated_registry):
        assert factory_module.get_plugin(self.fake_type) is None
        assert self.fake_type not in isolated_registry

    def test_module_without_expected_class_returns_none(self, monkeypatch, isolated_registry):
        monkeypatch.setitem(sys.modules, self.module_name, types.ModuleType(self.module_name))
        assert factory_module.get_plugin(self.fake_type) is None
        assert self.fake_type not in isolated_registry


class TestCreateMockServer:
    def test_returns_none_when_no_plugin(self, monkeypatch):
        monkeypatch.setattr(factory_module, "get_plugin", lambda exchange_type: None)
        assert factory_module.create_mock_server(ExchangeType.MOCK) is None

    def test_explicit_trading_pairs_replace_defaults(self):
        server = factory_module.create_mock_server(
            ExchangeType.MOCK, port=0, trading_pairs=[("ADA-USDT", "5m", 0.5)]
        )
        assert server.trading_pairs == {"ADA-USDT": 0.5}
        assert set(server.candles["ADA-USDT"]) == {"5m"}

    def test_defaults_seed_three_pairs(self):
        server = factory_module.create_mock_server(ExchangeType.MOCK, port=0)
        assert server.trading_pairs == {
            "BTC-USDT": 50000.0,
            "ETH-USDT": 3000.0,
            "SOL-USDT": 100.0,
        }
        assert all(len(server.candles[p]["1m"]) == 200 for p in server.trading_pairs)
