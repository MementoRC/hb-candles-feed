"""
Behavioural coverage tests for ExchangeURLPatcher.
"""

import sys
import types

import pytest

from candles_feed.adapters.binance import constants as binance_constants
from candles_feed.mocking_resources.core import url_patcher as url_patcher_module
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.core.url_patcher import ExchangeURLPatcher
from candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin import MockedPlugin

HOST, PORT = "127.0.0.1", 9999


class BarePlugin:
    """Plugin stand-in that supplies no URLs at all."""

    def get_patched_urls(self, host, port):
        return {}


@pytest.fixture
def plugin():
    return MockedPlugin(ExchangeType.MOCK)


@pytest.fixture
def fake_module(monkeypatch):
    module = types.ModuleType("fake_constants")
    module.REST = "https://real.example"
    module.WSS = "wss://real.example"
    monkeypatch.setitem(sys.modules, "fake_constants", module)
    return module


def route_to_fake(monkeypatch, patcher):
    monkeypatch.setattr(
        patcher,
        "_get_adapter_constants_module",
        lambda: ("fake_constants", {"rest": "REST", "ws": "WSS"}),
    )


class TestPatchAndRestore:
    def test_patch_rewrites_binance_constants_then_restore_reverts(self, monkeypatch, plugin):
        # monkeypatch guarantees the module is reset even if an assertion fails
        monkeypatch.setattr(binance_constants, "SPOT_REST_URL", binance_constants.SPOT_REST_URL)
        monkeypatch.setattr(binance_constants, "SPOT_WSS_URL", binance_constants.SPOT_WSS_URL)
        original = (binance_constants.SPOT_REST_URL, binance_constants.SPOT_WSS_URL)
        patcher = ExchangeURLPatcher(ExchangeType.BINANCE_SPOT, HOST, PORT)

        assert patcher.patch_urls(plugin) is True
        patched = (binance_constants.SPOT_REST_URL, binance_constants.SPOT_WSS_URL)
        assert patched == (f"http://{HOST}:{PORT}", f"ws://{HOST}:{PORT}/ws")
        assert patcher.original_urls["candles_feed.adapters.binance.constants"] == {
            "SPOT_REST_URL": original[0],
            "SPOT_WSS_URL": original[1],
        }

        assert patcher.restore_urls() is True
        restored = (binance_constants.SPOT_REST_URL, binance_constants.SPOT_WSS_URL)
        assert restored == original
        assert patcher.original_urls == {}

    def test_patch_uses_default_urls_when_plugin_supplies_none(self, monkeypatch, fake_module):
        patcher = ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT)
        route_to_fake(monkeypatch, patcher)
        assert patcher.patch_urls(BarePlugin()) is True
        patched = (fake_module.REST, fake_module.WSS)
        assert patched == (f"http://{HOST}:{PORT}", f"ws://{HOST}:{PORT}/ws")

    def test_patch_skips_attributes_missing_from_module(self, monkeypatch, fake_module, plugin):
        del fake_module.WSS
        patcher = ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT)
        route_to_fake(monkeypatch, patcher)
        assert patcher.patch_urls(plugin) is True
        patched_rest = fake_module.REST
        assert patched_rest == f"http://{HOST}:{PORT}"
        assert not hasattr(fake_module, "WSS")
        assert patcher.original_urls["fake_constants"] == {"REST": "https://real.example"}

    def test_patch_fails_without_module_mapping(self, monkeypatch, plugin):
        patcher = ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT)
        monkeypatch.setattr(patcher, "_get_adapter_constants_module", lambda: None)
        assert patcher.patch_urls(plugin) is False
        assert patcher.original_urls == {}

    def test_patch_fails_when_module_cannot_be_imported(self, plugin):
        patcher = ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT)
        # generic fallback points at candles_feed.adapters.mock.constants, which does not exist
        assert patcher.patch_urls(plugin) is False

    def test_patch_reports_unexpected_errors(self, monkeypatch, fake_module):
        class Exploding:
            def get_patched_urls(self, host, port):
                raise RuntimeError("boom")

        patcher = ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT)
        route_to_fake(monkeypatch, patcher)
        assert patcher.patch_urls(Exploding()) is False
        assert fake_module.REST == "https://real.example"

    def test_restore_without_patches_is_a_noop(self):
        assert ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT).restore_urls() is True

    def test_restore_skips_attributes_no_longer_present(self, monkeypatch, fake_module, plugin):
        patcher = ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT)
        route_to_fake(monkeypatch, patcher)
        patcher.patch_urls(plugin)
        del fake_module.WSS
        assert patcher.restore_urls() is True
        assert fake_module.REST == "https://real.example"
        assert not hasattr(fake_module, "WSS")

    def test_restore_tolerates_unimportable_module(self):
        patcher = ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT)
        patcher.original_urls = {"definitely_not_a_module_xyz": {"A": "b"}}
        assert patcher.restore_urls() is True
        assert patcher.original_urls == {}

    def test_restore_reports_unexpected_errors(self, monkeypatch):
        def explode(name):
            raise RuntimeError("boom")

        patcher = ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT)
        patcher.original_urls = {"fake_constants": {"REST": "x"}}
        monkeypatch.setattr(url_patcher_module.importlib, "import_module", explode)
        assert patcher.restore_urls() is False
        assert patcher.original_urls == {"fake_constants": {"REST": "x"}}


class TestModuleMapping:
    @pytest.mark.parametrize(
        ("exchange_type", "module", "rest", "ws"),
        [
            (
                ExchangeType.BINANCE_SPOT,
                "candles_feed.adapters.binance.constants",
                "SPOT_REST_URL",
                "SPOT_WSS_URL",
            ),
            (
                ExchangeType.BINANCE_PERPETUAL,
                "candles_feed.adapters.binance.constants",
                "PERPETUAL_REST_URL",
                "PERPETUAL_WSS_URL",
            ),
            (
                ExchangeType.AEVO_PERPETUAL,
                "candles_feed.adapters.aevo.constants",
                "REST_URL",
                "WSS_URL",
            ),
            (
                ExchangeType.BITGET_SPOT,
                "candles_feed.adapters.bitget.constants",
                "SPOT_REST_URL",
                "WSS_URL",
            ),
        ],
    )
    def test_explicit_mappings(self, exchange_type, module, rest, ws):
        patcher = ExchangeURLPatcher(exchange_type, HOST, PORT)
        assert patcher._get_adapter_constants_module() == (module, {"rest": rest, "ws": ws})

    @pytest.mark.parametrize(
        "exchange_type", [t for t in ExchangeType if t is not ExchangeType.MOCK]
    )
    def test_every_real_exchange_maps_to_its_adapter_package(self, exchange_type):
        patcher = ExchangeURLPatcher(exchange_type, HOST, PORT)
        module, attrs = patcher._get_adapter_constants_module()
        assert module.startswith("candles_feed.adapters.")
        assert module.endswith(".constants")
        assert set(attrs) == {"rest", "ws"}

    def test_unmapped_type_falls_back_to_spot_naming(self):
        patcher = ExchangeURLPatcher(ExchangeType.MOCK, HOST, PORT)
        assert patcher._get_adapter_constants_module() == (
            "candles_feed.adapters.mock.constants",
            {"rest": "SPOT_REST_URL", "ws": "SPOT_WSS_URL"},
        )

    def test_unmapped_perpetual_falls_back_to_perpetual_naming(self):
        fake_type = types.SimpleNamespace(value="newex_perpetual")
        patcher = ExchangeURLPatcher(fake_type, HOST, PORT)
        assert patcher._get_adapter_constants_module() == (
            "candles_feed.adapters.newex.constants",
            {"rest": "PERPETUAL_REST_URL", "ws": "PERPETUAL_WSS_URL"},
        )
