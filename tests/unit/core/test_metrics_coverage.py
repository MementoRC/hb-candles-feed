"""Behaviour tests for candles_feed.core.metrics."""

from unittest.mock import MagicMock

import pytest

from candles_feed.core import metrics as metrics_mod
from candles_feed.core.metrics import (
    MetricsCollector,
    OperationalMetrics,
    PerformanceTracker,
    track_async_operation,
    track_operation,
)


@pytest.fixture
def monitoring():
    return MagicMock()


@pytest.fixture
def collector(monitoring):
    return MetricsCollector(monitoring)


def _calls(monitoring):
    return {c.args[0]: c.args[1:] for c in monitoring.record_metric.call_args_list}


def test_operational_metrics_to_dict():
    m = OperationalMetrics(total_requests=3)
    d = m.to_dict()
    assert d["total_requests"] == 3
    assert set(d) == set(OperationalMetrics.__dataclass_fields__)


def test_default_monitoring_uses_singleton(mocker):
    sentinel = MagicMock()
    mocker.patch.object(metrics_mod.MonitoringManager, "get_instance", return_value=sentinel)
    assert MetricsCollector().monitoring is sentinel


class TestConnections:
    def test_created_and_closed(self, collector, monitoring):
        collector.record_connection_created("binance")
        assert collector.metrics.total_connections_created == 1
        assert collector.metrics.active_connections == 1
        assert _calls(monitoring)["active_connections"] == (1, {"exchange": "binance"})

        collector.record_connection_closed()
        collector.record_connection_closed()
        assert collector.metrics.active_connections == 0
        assert monitoring.record_metric.call_args.args == ("active_connections", 0, None)

    def test_error(self, collector, monitoring):
        collector.record_connection_error("kraken")
        assert collector.metrics.connection_errors == 1
        assert collector.metrics.total_errors == 1
        assert _calls(monitoring)["connection_errors_total"] == (1, {"exchange": "kraken"})

    def test_pool_stats(self, collector, monitoring):
        collector.update_connection_pool_stats({"total_connections": 8, "available_connections": 3})
        assert collector.metrics.connection_pool_size == 8
        assert collector.metrics.active_connections == 3
        monitoring.record_metric.assert_called_once_with("connection_pool_size", 8)


class TestRequests:
    def test_started_tags(self, collector, monitoring):
        collector.record_request_started("GET", "/x")
        collector.record_request_started()
        calls = monitoring.record_metric.call_args_list
        assert calls[0].args == ("requests_total", 1, {"method": "GET", "endpoint": "/x"})
        assert calls[1].args == ("requests_total", 2, None)

    def test_completed_success_and_failure(self, collector, monitoring):
        collector.record_request_started()
        collector.record_request_completed(0.5, True, "GET", "/x")
        collector.record_request_completed(1.5, False)
        assert collector.metrics.successful_requests == 1
        assert collector.metrics.failed_requests == 1
        assert collector.metrics.total_errors == 1
        first = monitoring.record_timing.call_args_list[0].args
        assert first == ("request", 0.5, {"status": "success", "method": "GET", "endpoint": "/x"})
        assert monitoring.record_timing.call_args_list[1].args[2] == {"status": "error"}
        assert collector.metrics.request_latency_p50 == 1.5

    def test_latency_percentiles_and_truncation(self, collector):
        collector._update_latency_percentiles()  # empty: no-op
        assert collector.metrics.request_latency_p50 == 0.0
        collector._request_times = [float(i) for i in range(1500)]
        collector._update_latency_percentiles()
        assert len(collector._request_times) == 1000
        assert collector.metrics.request_latency_p50 == 1000.0
        assert collector.metrics.request_latency_p95 == 1450.0
        assert collector.metrics.request_latency_p99 == 1490.0


class TestStreams:
    def test_lifecycle(self, collector, monitoring):
        collector.record_stream_started("binance", "BTC-USDT")
        collector.record_stream_started()
        assert collector.metrics.active_streams == 2
        collector.record_stream_disconnected("binance", "BTC-USDT")
        assert collector.metrics.active_streams == 1
        assert collector.metrics.stream_disconnections == 1
        collector.record_stream_reconnected("binance")
        assert collector.metrics.stream_reconnections == 1
        calls = _calls(monitoring)
        assert calls["stream_reconnections_total"] == (1, {"exchange": "binance"})
        assert calls["stream_disconnections_total"] == (
            1,
            {"exchange": "binance", "symbol": "BTC-USDT"},
        )

    def test_disconnect_never_negative(self, collector):
        collector.record_stream_disconnected()
        assert collector.metrics.active_streams == 0

    def test_reconnected_no_tags(self, collector, monitoring):
        collector.record_stream_reconnected()
        assert monitoring.record_metric.call_args.args == ("stream_reconnections_total", 1, None)


class TestProcessing:
    def test_candles_processed(self, collector, monitoring, mocker):
        mocker.patch.object(metrics_mod.time, "time", return_value=collector._start_time + 10)
        collector.record_candles_processed(100, "binance")
        assert collector.metrics.candles_processed == 100
        assert collector.metrics.candles_per_second == pytest.approx(10.0)
        assert _calls(monitoring)["candles_processed_total"] == (100, {"exchange": "binance"})

    def test_processing_error_rate(self, collector, monitoring):
        collector.metrics.total_requests = 1
        collector.metrics.candles_processed = 3
        collector.record_processing_error("binance")
        assert collector.metrics.processing_errors == 1
        assert collector.metrics.total_errors == 1
        assert collector.metrics.error_rate == pytest.approx(1 / 4)
        assert collector.metrics.last_error_time > 0
        assert _calls(monitoring)["error_rate"][1] == {"exchange": "binance"}

    def test_summary(self, collector):
        collector.metrics.request_latency_p50 = 0.25
        summary = collector.get_summary()
        assert summary["latency"]["p50_ms"] == 250
        assert summary["metrics"]["total_requests"] == 0
        assert set(summary["rates"]) == {"requests_per_second", "candles_per_second", "error_rate"}
        assert summary["uptime_seconds"] >= 0


class TestTrackOperation:
    def test_success(self, collector, monitoring):
        with track_operation(collector, "op", exchange="x"):
            pass
        name, _, tags = monitoring.record_timing.call_args.args
        assert name == "operation_op"
        assert tags == {"exchange": "x", "status": "success"}

    def test_failure(self, collector, monitoring):
        with pytest.raises(ValueError), track_operation(collector, "op"):
            raise ValueError("bad")
        assert monitoring.record_timing.call_args.args[2] == {"status": "error"}

    async def test_async_success(self, collector, monitoring):
        async with track_async_operation(collector, "aop", a="b"):
            pass
        name, _, tags = monitoring.record_timing.call_args.args
        assert name == "async_operation_aop"
        assert tags == {"a": "b", "status": "success"}

    async def test_async_failure(self, collector, monitoring):
        with pytest.raises(RuntimeError):
            async with track_async_operation(collector, "aop"):
                raise RuntimeError("bad")
        assert monitoring.record_timing.call_args.args[2] == {"status": "error"}


class TestPerformanceTracker:
    def test_default_collector(self, mocker):
        mocker.patch.object(metrics_mod.MonitoringManager, "get_instance", return_value=MagicMock())
        tracker = PerformanceTracker()
        assert isinstance(tracker.collector, MetricsCollector)
        assert tracker._profiler is None

    def test_track_request_without_profiler(self, collector):
        tracker = PerformanceTracker(collector)
        with tracker.track_request("GET", "/a"):
            pass
        assert collector.metrics.total_requests == 1
        assert collector.metrics.successful_requests == 1

    def test_track_request_failure_with_profiler(self, collector):
        tracker = PerformanceTracker(collector, enable_detailed_profiling=True)
        with pytest.raises(ValueError), tracker.track_request("POST", "/b"):
            raise ValueError("x")
        assert collector.metrics.failed_requests == 1
        assert tracker._profiler.metrics[0].operation_name == "POST /b"
        assert tracker._profiler.metrics[0].success is False

    async def test_track_stream(self, collector):
        tracker = PerformanceTracker(collector)
        async with tracker.track_stream("binance", "BTC-USDT"):
            assert collector.metrics.active_streams == 1
        assert collector.metrics.active_streams == 1
        with pytest.raises(RuntimeError):
            async with tracker.track_stream("binance", "BTC-USDT"):
                raise RuntimeError("drop")
        assert collector.metrics.stream_disconnections == 1

    def test_report(self, collector, monitoring):
        monitoring.get_health_status.return_value = {"status": "healthy"}
        plain = PerformanceTracker(collector).get_performance_report()
        assert plain["monitoring_health"] == {"status": "healthy"}
        assert "detailed_profiling" not in plain

        detailed = PerformanceTracker(collector, enable_detailed_profiling=True)
        with detailed.track_request("GET", "/a"):
            pass
        assert detailed.get_performance_report()["detailed_profiling"]["total_operations"] == 1
