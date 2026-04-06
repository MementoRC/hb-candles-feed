"""Auto-skip live tests in CI environments."""

import os

import pytest

# Detect CI environment (GitHub Actions, GitLab CI, etc.)
IS_CI = os.environ.get("CI", "").lower() in ("true", "1")


def pytest_collection_modifyitems(config, items):
    """Skip all live-marked tests when running in CI."""
    if not IS_CI:
        return

    skip_live = pytest.mark.skip(reason="Live tests disabled in CI (exchange APIs geo-blocked)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
