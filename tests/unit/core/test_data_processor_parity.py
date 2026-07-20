"""Passive-vs-compiled parity tests for :mod:`candles_feed.core.data_processor`.

These tests build the augmented-pure-python ``DataProcessor`` module with the
dev-only ``hb-cython-framework`` and assert that the compiled (Cython) variant
behaves identically to the passive (plain Python) variant across the scenarios
exercised by ``tests/performance/test_benchmarks.py``.

The whole module is skipped when the dev-only build framework or Cython is not
installed (e.g. minimal/CI-lite environments), so this file carries no
``live``/``slow`` marker and is safe to run under ``pixi run check``.
"""

from __future__ import annotations

import importlib.util
from collections import deque
from datetime import datetime
from pathlib import Path

import pytest

from candles_feed.core import data_processor as passive_dp
from candles_feed.core.candle_data import CandleData

variant_builder = pytest.importorskip(
    "cython_framework.buildhook.variant_builder",
    reason="hb-cython-framework not installed (dev/CI-only)",
)
pytest.importorskip("Cython")


@pytest.fixture(scope="module")
def compiled_dp(tmp_path_factory):
    """Build the compiled augmented-pure-python variant and load it by path."""
    from cython_framework.testing.cython_test_case import CythonModuleType

    source = Path(passive_dp.__file__).resolve()
    build_dir = tmp_path_factory.mktemp("dp_variant_build")
    try:
        artifacts = variant_builder.build_variants(
            source,
            module_name="data_processor",
            build_dir=build_dir,
            variants=[CythonModuleType.COMPILED_AUGMENTED_PYTHON],
        )
    except variant_builder.VariantBuildError as exc:
        pytest.skip(f"compiled variant unavailable (toolchain): {exc}")

    so_path = Path(artifacts[CythonModuleType.COMPILED_AUGMENTED_PYTHON])
    # The extension's PyInit_ symbol is named after the `module_name` passed to
    # build_variants() above ("data_processor"), so the loader name must match -
    # a different name here raises "dynamic module does not define module
    # export function".
    spec = importlib.util.spec_from_file_location("data_processor", so_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_candle(timestamp: int, base_price: float = 50000.0) -> CandleData:
    """Build a CandleData instance for parity scenarios."""
    return CandleData(
        timestamp_raw=timestamp,
        open=base_price,
        high=base_price + 10.0,
        low=base_price - 10.0,
        close=base_price + 5.0,
        volume=100.0,
    )


def _uniform_series(base_time: int, count: int, interval: int) -> list[CandleData]:
    return [_make_candle(base_time + i * interval, 50000.0 + i) for i in range(count)]


def _sanitize_scenarios(base_time: int, interval: int) -> dict[str, list[CandleData]]:
    sorted_uniform = _uniform_series(base_time, 20, interval)

    with_gap = _uniform_series(base_time, 20, interval)
    del with_gap[8:10]

    unsorted = _uniform_series(base_time, 20, interval)
    unsorted[2], unsorted[15] = unsorted[15], unsorted[2]
    unsorted[5], unsorted[9] = unsorted[9], unsorted[5]

    single = [_make_candle(base_time)]

    return {
        "sorted_uniform": sorted_uniform,
        "with_gap": with_gap,
        "unsorted": unsorted,
        "single": single,
        "empty": [],
    }


@pytest.fixture(scope="module")
def base_time() -> int:
    return int(datetime.now().timestamp())


@pytest.mark.parametrize(
    "scenario",
    ["sorted_uniform", "with_gap", "unsorted", "single", "empty"],
)
def test_sanitize_candles_parity(compiled_dp, base_time, scenario):
    interval = 60
    candles = _sanitize_scenarios(base_time, interval)[scenario]

    passive_result = passive_dp.DataProcessor().sanitize_candles(candles, interval)
    compiled_result = compiled_dp.DataProcessor().sanitize_candles(candles, interval)

    assert [c.timestamp for c in passive_result] == [c.timestamp for c in compiled_result]


@pytest.mark.parametrize(
    "scenario",
    ["sorted_uniform", "with_gap", "unsorted", "single", "empty"],
)
def test_validate_candle_intervals_parity(compiled_dp, base_time, scenario):
    interval = 60
    candles = _sanitize_scenarios(base_time, interval)[scenario]

    passive_result = passive_dp.DataProcessor().validate_candle_intervals(candles, interval)
    compiled_result = compiled_dp.DataProcessor().validate_candle_intervals(candles, interval)

    assert passive_result == compiled_result


def test_process_candle_parity(compiled_dp, base_time):
    interval = 60
    initial = _uniform_series(base_time, 50, interval)

    passive_store: deque[CandleData] = deque(initial, maxlen=500)
    compiled_store: deque[CandleData] = deque(initial, maxlen=500)

    passive_processor = passive_dp.DataProcessor()
    compiled_processor = compiled_dp.DataProcessor()

    # append
    append_candle = _make_candle(base_time + 100 * interval)
    # prepend
    prepend_candle = _make_candle(base_time - interval)
    # mid-insert
    mid_candle = _make_candle(base_time + 20 * interval + 30)
    # duplicate-update (overwrite an existing timestamp)
    update_candle = _make_candle(base_time + 10 * interval, base_price=99999.0)

    for candle in (append_candle, prepend_candle, mid_candle, update_candle):
        passive_processor.process_candle(candle, passive_store)
        compiled_processor.process_candle(candle, compiled_store)

    assert [c.timestamp for c in passive_store] == [c.timestamp for c in compiled_store]


def test_get_cache_stats_parity(compiled_dp):
    passive_result = passive_dp.DataProcessor().get_cache_stats()
    compiled_result = compiled_dp.DataProcessor().get_cache_stats()

    assert passive_result == compiled_result
