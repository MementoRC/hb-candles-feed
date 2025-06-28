"""Unit tests for the PrometheusExporter."""

import pytest
from prometheus_client import REGISTRY

from candles_feed.core.metrics import MetricsCollector
from candles_feed.monitoring.prometheus_exporter import PrometheusExporter


@pytest.fixture
def metrics_collector() -> MetricsCollector:
    """Fixture for a MetricsCollector instance."""
    return MetricsCollector()


@pytest.fixture
def prometheus_exporter() -> PrometheusExporter:
    """Fixture for a PrometheusExporter instance.

    This fixture ensures the Prometheus registry is clean before each test,
    preventing errors from re-registering metrics.
    """
    # Get a list of all currently registered collectors
    collectors = list(REGISTRY._collectors)
    for collector in collectors:
        # Unregister only if it's not one of the default collectors
        if hasattr(collector, "collect"):
            REGISTRY.unregister(collector)

    # Return a new exporter, which will register its metrics
    return PrometheusExporter()


class TestPrometheusExporter:
    """Tests for the PrometheusExporter."""

    def test_initialization(self, prometheus_exporter: PrometheusExporter):
        """Test that all metrics are created on initialization."""
        assert hasattr(prometheus_exporter, "active_connections")
        assert hasattr(prometheus_exporter, "total_requests")
        assert hasattr(prometheus_exporter, "candles_processed")
        assert hasattr(prometheus_exporter, "request_latency_p95")

    def test_export_metrics_gauges(
        self,
        prometheus_exporter: PrometheusExporter,
        metrics_collector: MetricsCollector,
    ):
        """Test that gauge metrics are exported correctly."""
        metrics_collector.metrics.active_connections = 5
        metrics_collector.metrics.request_latency_p95 = 0.123

        prometheus_exporter.export_metrics(metrics_collector)

        assert prometheus_exporter.active_connections._value.get() == 5
        assert prometheus_exporter.request_latency_p95._value.get() == 0.123

    def test_export_metrics_counters(
        self,
        prometheus_exporter: PrometheusExporter,
        metrics_collector: MetricsCollector,
    ):
        """Test that counter metrics are incremented correctly."""
        # Initial state
        metrics_collector.metrics.total_requests = 100
        prometheus_exporter.export_metrics(metrics_collector)
        assert prometheus_exporter.total_requests._value.get() == 100

        # Increment requests
        metrics_collector.metrics.total_requests = 105
        prometheus_exporter.export_metrics(metrics_collector)
        assert prometheus_exporter.total_requests._value.get() == 105

        # No change, should not increment further
        prometheus_exporter.export_metrics(metrics_collector)
        assert prometheus_exporter.total_requests._value.get() == 105

    def test_full_metric_export(
        self,
        prometheus_exporter: PrometheusExporter,
        metrics_collector: MetricsCollector,
    ):
        """Test exporting a full set of metrics."""
        # Populate some data
        metrics_collector.metrics.active_connections = 2
        metrics_collector.metrics.total_connections_created = 10
        metrics_collector.metrics.total_requests = 500
        metrics_collector.metrics.successful_requests = 490
        metrics_collector.metrics.failed_requests = 10
        metrics_collector.metrics.candles_processed = 10000
        metrics_collector.metrics.error_rate = 0.02

        prometheus_exporter.export_metrics(metrics_collector)

        assert prometheus_exporter.active_connections._value.get() == 2
        assert prometheus_exporter.total_connections_created._value.get() == 10
        assert prometheus_exporter.total_requests._value.get() == 500
        assert prometheus_exporter.successful_requests._value.get() == 490
        assert prometheus_exporter.failed_requests._value.get() == 10
        assert prometheus_exporter.candles_processed._value.get() == 10000
        assert prometheus_exporter.error_rate._value.get() == 0.02
