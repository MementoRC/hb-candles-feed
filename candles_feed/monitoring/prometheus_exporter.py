"""Prometheus exporter for candles-feed metrics."""

from prometheus_client import Counter, Gauge

from candles_feed.core.metrics import MetricsCollector


class PrometheusExporter:
    """Exports candles-feed metrics to Prometheus format.

    This class integrates with the MetricsCollector to expose operational
    metrics for consumption by a Prometheus server.
    """

    def __init__(self):
        """Initialize the Prometheus exporter and define metrics."""
        # Connection metrics
        self.active_connections = Gauge("active_connections", "Number of active connections")
        self.total_connections_created = Counter(
            "connections_created_total", "Total connections created"
        )
        self.connection_errors = Counter("connection_errors_total", "Total connection errors")
        self.connection_pool_size = Gauge(
            "connection_pool_size", "Size of the connection pool"
        )

        # Request metrics
        self.total_requests = Counter("requests_total", "Total requests made")
        self.successful_requests = Counter(
            "successful_requests_total", "Total successful requests"
        )
        self.failed_requests = Counter("failed_requests_total", "Total failed requests")

        # Stream metrics
        self.active_streams = Gauge("active_streams", "Number of active streams")
        self.total_streams_created = Counter("streams_created_total", "Total streams created")
        self.stream_disconnections = Counter(
            "stream_disconnections_total", "Total stream disconnections"
        )
        self.stream_reconnections = Counter(
            "stream_reconnections_total", "Total stream reconnections"
        )

        # Data processing metrics
        self.candles_processed = Counter("candles_processed_total", "Total candles processed")
        self.candles_per_second = Gauge("candles_per_second", "Candles processed per second")
        self.processing_errors = Counter(
            "processing_errors_total", "Total data processing errors"
        )

        # Error metrics
        self.total_errors = Counter("errors_total", "Total errors")
        self.error_rate = Gauge("error_rate", "Error rate")

        # Latency percentiles
        self.request_latency_p50 = Gauge(
            "request_latency_p50_seconds", "50th percentile request latency"
        )
        self.request_latency_p95 = Gauge(
            "request_latency_p95_seconds", "95th percentile request latency"
        )
        self.request_latency_p99 = Gauge(
            "request_latency_p99_seconds", "99th percentile request latency"
        )

    def export_metrics(self, collector: MetricsCollector):
        """Update Prometheus metrics from the MetricsCollector.

        :param collector: The MetricsCollector instance to export from.
        """
        metrics = collector.metrics

        # Use the difference to increment counters, as MetricsCollector holds totals.
        # This makes the counters robust to application restarts if the collector state is lost.
        self.total_connections_created.inc(
            metrics.total_connections_created - self.total_connections_created._value.get()
        )
        self.connection_errors.inc(
            metrics.connection_errors - self.connection_errors._value.get()
        )
        self.total_requests.inc(metrics.total_requests - self.total_requests._value.get())
        self.successful_requests.inc(
            metrics.successful_requests - self.successful_requests._value.get()
        )
        self.failed_requests.inc(metrics.failed_requests - self.failed_requests._value.get())
        self.total_streams_created.inc(
            metrics.total_streams_created - self.total_streams_created._value.get()
        )
        self.stream_disconnections.inc(
            metrics.stream_disconnections - self.stream_disconnections._value.get()
        )
        self.stream_reconnections.inc(
            metrics.stream_reconnections - self.stream_reconnections._value.get()
        )
        self.candles_processed.inc(
            metrics.candles_processed - self.candles_processed._value.get()
        )
        self.processing_errors.inc(
            metrics.processing_errors - self.processing_errors._value.get()
        )
        self.total_errors.inc(metrics.total_errors - self.total_errors._value.get())

        # Set gauges to their current values
        self.active_connections.set(metrics.active_connections)
        self.connection_pool_size.set(metrics.connection_pool_size)
        self.active_streams.set(metrics.active_streams)
        self.candles_per_second.set(metrics.candles_per_second)
        self.error_rate.set(metrics.error_rate)
        self.request_latency_p50.set(metrics.request_latency_p50)
        self.request_latency_p95.set(metrics.request_latency_p95)
        self.request_latency_p99.set(metrics.request_latency_p99)
