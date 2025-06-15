"""
Unit tests for metrics collection and performance tracking.
"""

import asyncio
import time

import pytest

from candles_feed.core.metrics import (
    MetricsCollector,
    OperationalMetrics,
    PerformanceTracker,
    track_async_operation,
    track_operation,
)


class TestOperationalMetrics:
    """Tests for OperationalMetrics."""

    def test_default_metrics(self):
        """Test default metrics initialization."""
        metrics = OperationalMetrics()
        assert metrics.active_connections == 0
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.active_streams == 0
        assert metrics.candles_processed == 0
        assert metrics.total_errors == 0

    def test_to_dict(self):
        """Test metrics conversion to dictionary."""
        metrics = OperationalMetrics(
            active_connections=5, total_requests=100, successful_requests=95, failed_requests=5
        )

        result = metrics.to_dict()

        assert result["active_connections"] == 5
        assert result["total_requests"] == 100
        assert result["successful_requests"] == 95
        assert result["failed_requests"] == 5


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_collector_initialization(self):
        """Test collector initialization."""
        collector = MetricsCollector()
        assert collector.metrics.active_connections == 0
        assert collector.metrics.total_requests == 0

    def test_record_connection_created(self):
        """Test connection creation recording."""
        collector = MetricsCollector()

        collector.record_connection_created("binance")

        assert collector.metrics.total_connections_created == 1
        assert collector.metrics.active_connections == 1

    def test_record_connection_closed(self):
        """Test connection closure recording."""
        collector = MetricsCollector()

        # Create then close connection
        collector.record_connection_created()
        collector.record_connection_closed()

        assert collector.metrics.total_connections_created == 1
        assert collector.metrics.active_connections == 0

    def test_record_request_lifecycle(self):
        """Test complete request lifecycle."""
        collector = MetricsCollector()

        # Start request
        collector.record_request_started("GET", "/api/v1/klines")
        assert collector.metrics.total_requests == 1

        # Complete successfully
        collector.record_request_completed(0.5, True, "GET", "/api/v1/klines")
        assert collector.metrics.successful_requests == 1
        assert collector.metrics.failed_requests == 0

    def test_record_stream_lifecycle(self):
        """Test stream lifecycle recording."""
        collector = MetricsCollector()

        # Start stream
        collector.record_stream_started("binance", "BTCUSDT")
        assert collector.metrics.total_streams_created == 1
        assert collector.metrics.active_streams == 1

        # Disconnect stream
        collector.record_stream_disconnected("binance", "BTCUSDT")
        assert collector.metrics.active_streams == 0
        assert collector.metrics.stream_disconnections == 1

    def test_record_candles_processed(self):
        """Test candles processing recording."""
        collector = MetricsCollector()

        collector.record_candles_processed(10, "binance")
        collector.record_candles_processed(5, "binance")

        assert collector.metrics.candles_processed == 15
        assert collector.metrics.candles_per_second > 0

    def test_get_summary(self):
        """Test metrics summary generation."""
        collector = MetricsCollector()

        # Add some metrics
        collector.record_request_started()
        collector.record_request_completed(0.5, True)
        collector.record_candles_processed(10)

        summary = collector.get_summary()

        assert "uptime_seconds" in summary
        assert "metrics" in summary
        assert "rates" in summary
        assert "latency" in summary


class TestPerformanceTracker:
    """Tests for PerformanceTracker."""

    def test_tracker_initialization(self):
        """Test tracker initialization."""
        tracker = PerformanceTracker()
        assert tracker.collector is not None
        assert tracker.enable_detailed_profiling is False

    def test_track_request_context_manager(self):
        """Test request tracking context manager."""
        tracker = PerformanceTracker()

        with tracker.track_request("GET", "/api/v1/klines", "binance"):
            time.sleep(0.01)  # Simulate work

        assert tracker.collector.metrics.total_requests == 1
        assert tracker.collector.metrics.successful_requests == 1

    def test_track_request_with_exception(self):
        """Test request tracking with exception."""
        tracker = PerformanceTracker()

        # Verify exception is raised and metrics are recorded
        with (
            pytest.raises(ValueError, match="Test error"),
            tracker.track_request("GET", "/api/v1/klines"),
        ):
            raise ValueError("Test error")

        # Verify metrics were recorded despite the exception
        assert tracker.collector.metrics.total_requests == 1
        assert tracker.collector.metrics.failed_requests == 1

    @pytest.mark.asyncio
    async def test_track_stream_context_manager(self):
        """Test stream tracking context manager."""
        tracker = PerformanceTracker()

        async with tracker.track_stream("binance", "BTCUSDT"):
            pass  # Simulate stream work

        assert tracker.collector.metrics.total_streams_created == 1

    def test_get_performance_report(self):
        """Test performance report generation."""
        tracker = PerformanceTracker()

        # Add some metrics
        tracker.collector.record_request_started()
        tracker.collector.record_request_completed(0.5, True)

        report = tracker.get_performance_report()

        assert "operational_metrics" in report
        assert "monitoring_health" in report


class TestTrackingOperations:
    """Tests for tracking context managers."""

    def test_track_operation_success(self):
        """Test track_operation context manager with success."""
        collector = MetricsCollector()

        with track_operation(collector, "test_operation", tag1="value1"):
            time.sleep(0.01)

        # Verify timing was recorded
        metrics = collector.monitoring.get_metrics()
        assert "operation_test_operation_duration" in metrics

    @pytest.mark.asyncio
    async def test_track_async_operation_success(self):
        """Test track_async_operation context manager with success."""
        collector = MetricsCollector()

        async with track_async_operation(collector, "async_test", tag1="value1"):
            await asyncio.sleep(0.01)

        # Verify async timing was recorded
        metrics = collector.monitoring.get_metrics()
        assert "async_operation_async_test_duration" in metrics
