"""
Metrics collection and performance tracking for the Candle Feed framework.

This module provides comprehensive metrics collection, building on the existing
profiling infrastructure to provide operational visibility.
"""

import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Generator

from ..utils.profiling import PerformanceProfiler
from .monitoring import MonitoringManager


@dataclass
class OperationalMetrics:
    """Operational metrics for candles-feed components."""

    # Connection metrics
    active_connections: int = 0
    total_connections_created: int = 0
    connection_errors: int = 0
    connection_pool_size: int = 0

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    request_latency_p50: float = 0.0
    request_latency_p95: float = 0.0
    request_latency_p99: float = 0.0

    # Stream metrics
    active_streams: int = 0
    total_streams_created: int = 0
    stream_disconnections: int = 0
    stream_reconnections: int = 0

    # Data processing metrics
    candles_processed: int = 0
    candles_per_second: float = 0.0
    processing_errors: int = 0

    # Error metrics
    total_errors: int = 0
    error_rate: float = 0.0
    last_error_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for export."""
        return {
            field_name: getattr(self, field_name) for field_name in self.__dataclass_fields__.keys()
        }


class MetricsCollector:
    """Metrics collector with performance tracking integration."""

    def __init__(self, monitoring_manager: MonitoringManager | None = None):
        """Initialize metrics collector.

        :param monitoring_manager: MonitoringManager instance
        """
        self.monitoring = monitoring_manager or MonitoringManager.get_instance()
        self.metrics = OperationalMetrics()
        self._profiler = PerformanceProfiler()
        self._start_time = time.time()
        self._request_times: list[float] = []

    def record_connection_created(self, exchange: str = "") -> None:
        """Record a new connection creation.

        :param exchange: Exchange name for tagging
        """
        self.metrics.total_connections_created += 1
        self.metrics.active_connections += 1

        self.monitoring.record_metric(
            "connections_created_total",
            self.metrics.total_connections_created,
            {"exchange": exchange} if exchange else None,
        )

        self.monitoring.record_metric(
            "active_connections",
            self.metrics.active_connections,
            {"exchange": exchange} if exchange else None,
        )

    def record_connection_closed(self, exchange: str = "") -> None:
        """Record a connection closure.

        :param exchange: Exchange name for tagging
        """
        self.metrics.active_connections = max(0, self.metrics.active_connections - 1)

        self.monitoring.record_metric(
            "active_connections",
            self.metrics.active_connections,
            {"exchange": exchange} if exchange else None,
        )

    def record_connection_error(self, exchange: str = "") -> None:
        """Record a connection error.

        :param exchange: Exchange name for tagging
        """
        self.metrics.connection_errors += 1
        self.metrics.total_errors += 1

        self.monitoring.record_metric(
            "connection_errors_total",
            self.metrics.connection_errors,
            {"exchange": exchange} if exchange else None,
        )

    def record_request_started(self, method: str = "", endpoint: str = "") -> None:
        """Record a request start.

        :param method: HTTP method
        :param endpoint: API endpoint
        """
        self.metrics.total_requests += 1

        tags = {}
        if method:
            tags["method"] = method
        if endpoint:
            tags["endpoint"] = endpoint

        self.monitoring.record_metric(
            "requests_total", self.metrics.total_requests, tags if tags else None
        )

    def record_request_completed(
        self, duration: float, success: bool = True, method: str = "", endpoint: str = ""
    ) -> None:
        """Record a completed request.

        :param duration: Request duration in seconds
        :param success: Whether request was successful
        :param method: HTTP method
        :param endpoint: API endpoint
        """
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
            self.metrics.total_errors += 1

        # Track latency
        self._request_times.append(duration)
        self._update_latency_percentiles()

        # Record metrics
        tags = {"status": "success" if success else "error"}
        if method:
            tags["method"] = method
        if endpoint:
            tags["endpoint"] = endpoint

        self.monitoring.record_timing("request", duration, tags)
        self.monitoring.record_metric(
            "request_success_rate",
            self.metrics.successful_requests / max(1, self.metrics.total_requests),
            tags if tags else None,
        )

    def record_stream_started(self, exchange: str = "", symbol: str = "") -> None:
        """Record a stream start.

        :param exchange: Exchange name
        :param symbol: Trading pair symbol
        """
        self.metrics.total_streams_created += 1
        self.metrics.active_streams += 1

        tags = {}
        if exchange:
            tags["exchange"] = exchange
        if symbol:
            tags["symbol"] = symbol

        self.monitoring.record_metric(
            "streams_created_total", self.metrics.total_streams_created, tags if tags else None
        )

        self.monitoring.record_metric(
            "active_streams", self.metrics.active_streams, tags if tags else None
        )

    def record_stream_disconnected(self, exchange: str = "", symbol: str = "") -> None:
        """Record a stream disconnection.

        :param exchange: Exchange name
        :param symbol: Trading pair symbol
        """
        self.metrics.active_streams = max(0, self.metrics.active_streams - 1)
        self.metrics.stream_disconnections += 1

        tags = {}
        if exchange:
            tags["exchange"] = exchange
        if symbol:
            tags["symbol"] = symbol

        self.monitoring.record_metric(
            "stream_disconnections_total",
            self.metrics.stream_disconnections,
            tags if tags else None,
        )

        self.monitoring.record_metric(
            "active_streams", self.metrics.active_streams, tags if tags else None
        )

    def record_stream_reconnected(self, exchange: str = "", symbol: str = "") -> None:
        """Record a stream reconnection.

        :param exchange: Exchange name
        :param symbol: Trading pair symbol
        """
        self.metrics.stream_reconnections += 1

        tags = {}
        if exchange:
            tags["exchange"] = exchange
        if symbol:
            tags["symbol"] = symbol

        self.monitoring.record_metric(
            "stream_reconnections_total", self.metrics.stream_reconnections, tags if tags else None
        )

    def record_candles_processed(self, count: int, exchange: str = "") -> None:
        """Record processed candles.

        :param count: Number of candles processed
        :param exchange: Exchange name for tagging
        """
        self.metrics.candles_processed += count

        # Calculate processing rate
        elapsed = time.time() - self._start_time
        self.metrics.candles_per_second = self.metrics.candles_processed / max(1, elapsed)

        tags = {"exchange": exchange} if exchange else None

        self.monitoring.record_metric(
            "candles_processed_total", self.metrics.candles_processed, tags
        )

        self.monitoring.record_metric("candles_per_second", self.metrics.candles_per_second, tags)

    def record_processing_error(self, exchange: str = "") -> None:
        """Record a data processing error.

        :param exchange: Exchange name for tagging
        """
        self.metrics.processing_errors += 1
        self.metrics.total_errors += 1
        self.metrics.last_error_time = time.time()

        # Calculate error rate
        total_operations = (
            self.metrics.total_requests
            + self.metrics.candles_processed
            + self.metrics.total_streams_created
        )
        self.metrics.error_rate = self.metrics.total_errors / max(1, total_operations)

        tags = {"exchange": exchange} if exchange else None

        self.monitoring.record_metric(
            "processing_errors_total", self.metrics.processing_errors, tags
        )

        self.monitoring.record_metric("error_rate", self.metrics.error_rate, tags)

    def update_connection_pool_stats(self, stats: dict[str, Any]) -> None:
        """Update connection pool statistics.

        :param stats: Connection pool stats from NetworkClient
        """
        self.metrics.connection_pool_size = stats.get("total_connections", 0)
        self.metrics.active_connections = stats.get("available_connections", 0)

        self.monitoring.record_metric("connection_pool_size", self.metrics.connection_pool_size)

    def _update_latency_percentiles(self) -> None:
        """Update latency percentile calculations."""
        if not self._request_times:
            return

        # Keep only recent measurements (last 1000)
        if len(self._request_times) > 1000:
            self._request_times = self._request_times[-1000:]

        sorted_times = sorted(self._request_times)
        count = len(sorted_times)

        if count > 0:
            self.metrics.request_latency_p50 = sorted_times[int(count * 0.5)]
            self.metrics.request_latency_p95 = sorted_times[int(count * 0.95)]
            self.metrics.request_latency_p99 = sorted_times[int(count * 0.99)]

    def get_summary(self) -> dict[str, Any]:
        """Get comprehensive metrics summary.

        :return: Metrics summary dictionary
        """
        uptime = time.time() - self._start_time

        return {
            "uptime_seconds": uptime,
            "metrics": self.metrics.to_dict(),
            "rates": {
                "requests_per_second": self.metrics.total_requests / max(1, uptime),
                "candles_per_second": self.metrics.candles_per_second,
                "error_rate": self.metrics.error_rate,
            },
            "latency": {
                "p50_ms": self.metrics.request_latency_p50 * 1000,
                "p95_ms": self.metrics.request_latency_p95 * 1000,
                "p99_ms": self.metrics.request_latency_p99 * 1000,
            },
        }


@contextmanager
def track_operation(
    collector: MetricsCollector, operation_name: str, **tags
) -> Generator[None, None, None]:
    """Context manager for tracking operation performance.

    :param collector: MetricsCollector instance
    :param operation_name: Name of the operation
    :param tags: Additional tags for metrics
    """
    start_time = time.time()
    success = True

    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration = time.time() - start_time

        # Record operation metrics
        collector.monitoring.record_timing(
            f"operation_{operation_name}",
            duration,
            {**tags, "status": "success" if success else "error"},
        )


@asynccontextmanager
async def track_async_operation(
    collector: MetricsCollector, operation_name: str, **tags
) -> AsyncGenerator[None, None]:
    """Async context manager for tracking operation performance.

    :param collector: MetricsCollector instance
    :param operation_name: Name of the operation
    :param tags: Additional tags for metrics
    """
    start_time = time.time()
    success = True

    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration = time.time() - start_time

        # Record operation metrics
        collector.monitoring.record_timing(
            f"async_operation_{operation_name}",
            duration,
            {**tags, "status": "success" if success else "error"},
        )


class PerformanceTracker:
    """High-level performance tracking with integration to existing profiler."""

    def __init__(
        self,
        metrics_collector: MetricsCollector | None = None,
        enable_detailed_profiling: bool = False,
    ):
        """Initialize performance tracker.

        :param metrics_collector: MetricsCollector instance
        :param enable_detailed_profiling: Enable detailed profiling
        """
        self.collector = metrics_collector or MetricsCollector()
        self.enable_detailed_profiling = enable_detailed_profiling
        self._profiler = PerformanceProfiler() if enable_detailed_profiling else None

    @contextmanager
    def track_request(
        self, method: str = "", endpoint: str = "", exchange: str = ""
    ) -> Generator[None, None, None]:
        """Track a network request.

        :param method: HTTP method
        :param endpoint: API endpoint
        :param exchange: Exchange name
        """
        self.collector.record_request_started(method, endpoint)
        start_time = time.time()
        success = True

        try:
            if self._profiler:
                with self._profiler.measure(f"{method} {endpoint}"):
                    yield
            else:
                yield
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            self.collector.record_request_completed(duration, success, method, endpoint)

    @asynccontextmanager
    async def track_stream(
        self, exchange: str = "", symbol: str = ""
    ) -> AsyncGenerator[None, None]:
        """Track a WebSocket stream.

        :param exchange: Exchange name
        :param symbol: Trading pair symbol
        """
        self.collector.record_stream_started(exchange, symbol)

        try:
            yield
        except Exception:
            self.collector.record_stream_disconnected(exchange, symbol)
            raise

    def get_performance_report(self) -> dict[str, Any]:
        """Get comprehensive performance report.

        :return: Performance report dictionary
        """
        report = {
            "operational_metrics": self.collector.get_summary(),
            "monitoring_health": self.collector.monitoring.get_health_status(),
        }

        if self._profiler:
            report["detailed_profiling"] = self._profiler.get_metrics_summary()

        return report
