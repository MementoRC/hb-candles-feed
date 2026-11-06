"""Tests for the prometheus_client-unavailable fallback of http_server."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from candles_feed.monitoring import http_server as real_module


@pytest.fixture
def fallback_module(monkeypatch):
    """Load a private copy of http_server with prometheus_client import blocked."""
    monkeypatch.setitem(sys.modules, "prometheus_client", None)
    name = "candles_feed.monitoring._http_server_fallback"
    spec = importlib.util.spec_from_file_location(name, Path(real_module.__file__))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def test_fallback_defaults(fallback_module):
    assert fallback_module.PROMETHEUS_AVAILABLE is False
    assert fallback_module.REGISTRY is None
    assert "not available" in fallback_module.generate_latest()


async def test_fallback_handler_returns_placeholder(fallback_module):
    resp = await fallback_module.metrics_handler(MagicMock())
    assert "install prometheus_client" in resp.text
    assert resp.content_type == "text/plain"
