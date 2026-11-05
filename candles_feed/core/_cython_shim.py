"""No-op Cython shim for augmented-pure-python modules.

Lets a module carrying Cython pure-mode markers (``@cython.cclass`` and friends)
import ``cython`` and run as plain Python even when Cython is NOT installed. It is
only ever used on the passive (uncompiled) runtime path: when Cython is present
(build/dev/compiled envs) the real ``cython`` module is used instead, and the real
compiler recognises the markers at build time.

Deliberately vendored stub (the single sanctioned vendoring exception for the
Phase 2 augmented-pure-python conversion): candles-feed must add ZERO runtime
dependencies to stay "passive is free", so it cannot depend on Cython at runtime.
Keep it tiny.
"""

from __future__ import annotations

# Mirrors ``cython.compiled`` (always False on this pure-Python fallback path).
compiled = False


class _NoOp:
    """Universal inert stand-in for any ``cython.<attr>``.

    As a decorator (``@cython.cclass``) it returns the decorated object unchanged;
    as a type (``cython.int``) it is subscriptable and callable, returning itself
    so annotations/casts are inert; any attribute access returns another no-op.
    """

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and not kwargs:
            return args[0]
        return self

    def __getitem__(self, _item):
        return self

    def __getattr__(self, _name):
        return self


def __getattr__(name):  # PEP 562 module-level attribute hook
    """Return an inert no-op for any ``cython.<name>`` reference."""
    return _NoOp()
