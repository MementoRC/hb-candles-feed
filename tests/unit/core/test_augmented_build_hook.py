"""Unit tests for the augmented-compile build hook (issue #76, Phase 3).

These exercise the hook's env gate and fail-closed contract WITHOUT requiring the
maintainer-local ``hb-cython-framework`` or a C toolchain, so they run in every
environment. Compiled-vs-passive behaviour parity is covered separately by
``test_data_processor_parity.py`` (run in the ``accel`` env).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("hatchling", reason="hatchling (build backend) not installed")

# hatch_build.py is a root-level build module, not a package member; load by path.
_HOOK_PATH = Path(__file__).resolve().parents[3] / "hatch_build.py"
_spec = importlib.util.spec_from_file_location("candles_feed_hatch_build", _HOOK_PATH)
hatch_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hatch_build)


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "Yes", "on", " on "])
def test_gate_truthy_values_enable_compile(value):
    assert hatch_build._accelerated_build_requested({"HB_COMPILE_AUGMENTED": value}) is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "maybe"])
def test_gate_falsy_values_stay_passive(value):
    assert hatch_build._accelerated_build_requested({"HB_COMPILE_AUGMENTED": value}) is False


def test_gate_absent_is_passive():
    assert hatch_build._accelerated_build_requested({}) is False


def test_passive_initialize_is_strict_noop(monkeypatch):
    """Gate off -> initialize() must never consult the framework (AC1)."""
    monkeypatch.delenv("HB_COMPILE_AUGMENTED", raising=False)

    def _boom(*_args, **_kwargs):
        raise AssertionError("framework must not be consulted in passive mode")

    monkeypatch.setattr(hatch_build, "_delegate_to_framework", _boom)

    hook = hatch_build.CandlesFeedBuildHook.__new__(hatch_build.CandlesFeedBuildHook)
    hook.initialize("1.0.0", {})  # returns without touching hatchling state


def test_delegate_fails_closed_when_framework_missing(monkeypatch):
    """Gate on but framework absent -> warn, skip, return False; never raise (AC3)."""
    warnings: list[str] = []
    fake_hook = SimpleNamespace(app=SimpleNamespace(display_warning=warnings.append))

    # Force the lazy import to fail even if the framework happens to be installed.
    monkeypatch.setitem(sys.modules, "cython_framework.buildhook.hook", None)

    delegated = hatch_build._delegate_to_framework(fake_hook, "1.0.0", {})

    assert delegated is False
    assert warnings and "hb-cython-framework is unavailable" in warnings[0]


def test_delegate_succeeds_and_reconstructs_hook_args(monkeypatch):
    """Gate on and framework present -> construct the framework hook from the
    exact hatchling args, call initialize(), and return True (AC2 delegation)."""
    recorded = {}

    class _StubFrameworkHook:
        def __init__(self, root, config, build_config, metadata, directory, target_name, app):
            recorded["ctor"] = (root, config, build_config, metadata, directory, target_name, app)

        def initialize(self, version, build_data):
            recorded["init"] = (version, build_data)

    fake_module = SimpleNamespace(AugmentedCythonBuildHook=_StubFrameworkHook)
    for _name in ("cython_framework", "cython_framework.buildhook"):
        monkeypatch.setitem(sys.modules, _name, SimpleNamespace())
    monkeypatch.setitem(sys.modules, "cython_framework.buildhook.hook", fake_module)

    hook = SimpleNamespace(
        root="/repo",
        config={"path": "hatch_build.py"},
        build_config={"bc": 1},
        metadata="META",
        directory="/dist",
        target_name="wheel",
        app=SimpleNamespace(display_warning=lambda *_args, **_kwargs: None),
    )

    delegated = hatch_build._delegate_to_framework(hook, "3.0.0", {"pure_python": False})

    assert delegated is True
    assert recorded["ctor"] == (
        "/repo",
        {"path": "hatch_build.py"},
        {"bc": 1},
        "META",
        "/dist",
        "wheel",
        hook.app,
    )
    assert recorded["init"] == ("3.0.0", {"pure_python": False})


def test_initialize_under_gate_delegates(monkeypatch):
    """Gate on -> initialize() routes through _delegate_to_framework (AC2 dispatch)."""
    monkeypatch.setenv("HB_COMPILE_AUGMENTED", "1")

    captured = {}

    def _capture(_hook, version, build_data):
        captured["call"] = (version, build_data)
        return True

    monkeypatch.setattr(hatch_build, "_delegate_to_framework", _capture)

    hook = hatch_build.CandlesFeedBuildHook.__new__(hatch_build.CandlesFeedBuildHook)
    hook.initialize("2.0.0", {"k": "v"})

    assert captured["call"] == ("2.0.0", {"k": "v"})
