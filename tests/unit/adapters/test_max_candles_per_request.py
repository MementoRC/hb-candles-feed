"""MAX_CANDLES_PER_REQUEST must mirror each exchange package's REST page-size constant."""

import importlib

import pytest

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry

ExchangeRegistry.discover_adapters()

_REGISTERED = sorted(ExchangeRegistry._adapters.items())


def _package_constant(adapter_class: type) -> int | None:
    package = adapter_class.__module__.rsplit(".", 1)[0]
    try:
        constants = importlib.import_module(f"{package}.constants")
    except ModuleNotFoundError:
        return None
    return getattr(constants, "MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST", None)


def test_base_adapter_default() -> None:
    assert BaseAdapter.MAX_CANDLES_PER_REQUEST == 500


@pytest.mark.parametrize(("name", "adapter_class"), _REGISTERED, ids=[n for n, _ in _REGISTERED])
def test_adapter_max_candles_matches_package_constant(name: str, adapter_class: type) -> None:
    expected = _package_constant(adapter_class)
    if expected is None:
        pytest.skip(f"{name} has no MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST constant")
    assert expected == adapter_class.MAX_CANDLES_PER_REQUEST


def test_all_exchange_packages_are_covered() -> None:
    covered = {a.__module__.rsplit(".", 1)[0] for _, a in _REGISTERED if _package_constant(a)}
    assert len(covered) >= 21
