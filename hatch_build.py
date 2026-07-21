"""Hatchling build hook for candles-feed — issue #76, Phase 3 (compile-on-accelerated).

PASSIVE BY DEFAULT. This hook is a strict no-op unless the environment variable
``HB_COMPILE_AUGMENTED`` is truthy (one of ``{1, true, yes, on}``, case-insensitive).
Under a normal install — and under the hummingbot gate's editable install — it adds
ZERO dependencies and produces the current pure-Python behavior (AC1).

When ``HB_COMPILE_AUGMENTED`` is set, it delegates to the maintainer-local
``hb-cython-framework`` build hook, which discovers augmented-pure-python modules by
pragma (``# cython: augmented_pure_python=True``, via the framework's ``is_augmented``
scan — no central manifest) and compiles them (e.g. ``data_processor.py`` -> ``.so``)
with Cython (AC2).

PUBLISHING BOUNDARY (AC3). ``cython`` is never added to ``[project.dependencies]`` and
``hb-cython-framework`` is never added to ``[build-system].requires`` or runtime deps.
Real Cython is build/dev-only and exposed via the optional ``candles-feed[accelerated]``
extra. The framework hook is referenced ONLY via a lazy, guarded import that runs solely
when ``HB_COMPILE_AUGMENTED`` is set; the framework is supplied on the build path by the
hummingbot accelerated env (orchestrator-owned), never by this package's published
metadata. The hook FAILS CLOSED — it skips compilation instead of raising — when the
framework is unavailable, so a plain dev install never breaks.

The accelerated-tier wiring that actually sets ``HB_COMPILE_AUGMENTED=1`` and provides the
framework on the build path is out of scope here (orchestrator-owned; lives in the
hummingbot ``_for_accel/cython-framework`` branch).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

#: Environment gate that opts a build into compiling the augmented modules.
_ENV_GATE = "HB_COMPILE_AUGMENTED"

#: Truthy spellings that enable the accelerated (native) compile.
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _accelerated_build_requested(environ: Mapping[str, str] | None = None) -> bool:
    """Return True iff the accelerated compile is explicitly requested (AC1)."""
    env = os.environ if environ is None else environ
    return env.get(_ENV_GATE, "").strip().lower() in _TRUTHY


def _delegate_to_framework(
    hook: BuildHookInterface, version: str, build_data: dict[str, Any]
) -> bool:
    """Lazily import and run the hb-cython-framework build hook.

    Returns True if compilation was delegated, or False if the framework was
    unavailable (fail-closed skip per AC3). Genuine compile errors raised by the
    framework are allowed to propagate, so an accelerated build never silently
    ships an uncompiled wheel.
    """
    try:
        from cython_framework.buildhook.hook import AugmentedCythonBuildHook
    except ImportError as exc:  # AC3: fail closed — framework not on the build path.
        hook.app.display_warning(
            f"{_ENV_GATE} is set but hb-cython-framework is unavailable "
            f"({exc}); skipping augmented compilation and building the passive "
            f"pure-Python wheel."
        )
        return False

    # Both hooks derive from hatchling's BuildHookInterface, so the framework
    # hook is reconstructed from the exact arguments hatchling handed us.
    framework_hook = AugmentedCythonBuildHook(
        hook.root,
        hook.config,
        hook.build_config,
        hook.metadata,
        hook.directory,
        hook.target_name,
        hook.app,
    )
    framework_hook.initialize(version, build_data)
    return True


class CandlesFeedBuildHook(BuildHookInterface):
    """Compile augmented modules only when explicitly gated; otherwise a no-op."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if not _accelerated_build_requested():
            # AC1: passive by default — no framework import, no Cython, no deps.
            return
        _delegate_to_framework(self, version, build_data)
