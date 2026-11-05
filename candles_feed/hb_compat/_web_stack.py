"""Locate the throttler / REST stack the hb_compat bridge runs on.

The stack is provided either by hummingbot (``hummingbot.core.api_throttler`` and
``hummingbot.core.web_assistant``) or, standalone, by the ``hb-web-assistant`` package
(``web_assistant.throttler`` and ``web_assistant``). hummingbot is tried first. Nothing
here imports either at module load: ``import_web_stack`` raises ``ImportError`` when
neither is installed, so callers keep their existing "not available" handling.
"""

from importlib import import_module
from types import ModuleType

_ROOTS: dict[str, tuple[str, ...]] = {
    "throttler": ("hummingbot.core.api_throttler", "web_assistant.throttler"),
    "web": ("hummingbot.core.web_assistant", "web_assistant"),
}


def import_web_stack(area: str, module: str) -> ModuleType:
    """Import ``module`` from the first available provider of ``area``.

    :param area: ``"throttler"`` or ``"web"``
    :param module: Dotted module path relative to the provider root
    :return: The imported module
    :raises ImportError: If no provider has the module
    """
    last_error: ImportError | None = None
    for root in _ROOTS[area]:
        try:
            return import_module(f"{root}.{module}")
        except ImportError as exc:
            last_error = exc
    raise last_error or ImportError(f"no provider for {area}.{module}")
