"""Tests for the prometheus_client-unavailable fallback of prometheus_exporter."""

import importlib.util
import sys
from pathlib import Path

import pytest

from candles_feed.core.metrics import MetricsCollector
from candles_feed.monitoring import prometheus_exporter as real_module


@pytest.fixture
def fallback_module(monkeypatch):
    """Load a private copy of the module with prometheus_client import blocked."""
    monkeypatch.setitem(sys.modules, "prometheus_client", None)
    name = "_prometheus_exporter_fallback"
    spec = importlib.util.spec_from_file_location(name, Path(real_module.__file__))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def test_fallback_flags_unavailable(fallback_module):
    assert fallback_module.PROMETHEUS_AVAILABLE is False


def test_stub_counter_and_gauge_are_chainable_noops(fallback_module):
    counter = fallback_module.Counter("n", "doc")
    gauge = fallback_module.Gauge("g", "doc")
    assert counter.labels(a="b") is counter
    assert gauge.labels(a="b") is gauge
    assert counter.inc(5) is None
    assert gauge.set(3) is None


def test_export_metrics_noop_when_unavailable(fallback_module):
    exporter = fallback_module.PrometheusExporter()
    collector = MetricsCollector()
    collector.metrics.total_requests = 5
    # Stub counters have no `_value`; reaching them would raise AttributeError.
    assert exporter.export_metrics(collector) is None
