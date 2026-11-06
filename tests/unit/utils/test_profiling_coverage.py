"""Behaviour tests for candles_feed.utils.profiling."""

from unittest.mock import MagicMock

import pytest

from candles_feed.utils import profiling
from candles_feed.utils.profiling import (
    BenchmarkResult,
    BenchmarkSuite,
    PerformanceProfiler,
    profile_performance,
)


@pytest.fixture
def profiler():
    p = PerformanceProfiler(enable_memory_tracking=False)
    return p


class TestProfiler:
    def test_measure_success(self, profiler):
        with profiler.measure("op", tag="v"):
            pass
        m = profiler.metrics[0]
        assert m.operation_name == "op"
        assert m.success is True and m.error is None
        assert m.metadata == {"tag": "v"}
        assert m.memory_current_mb == 0.0

    def test_measure_failure_records_error(self, profiler):
        with pytest.raises(ValueError), profiler.measure("op"):
            raise ValueError("kaput")
        assert profiler.metrics[0].success is False
        assert profiler.metrics[0].error == "kaput"

    def test_measure_with_memory(self, mocker):
        p = PerformanceProfiler(enable_memory_tracking=True)
        mocker.patch.object(p, "_get_memory_usage", side_effect=[10.0, 25.0])
        with p.measure("op"):
            pass
        assert p.metrics[0].memory_peak_mb == 25.0
        assert p.metrics[0].memory_current_mb == 25.0

    async def test_measure_async(self, profiler):
        async with profiler.measure_async("aop", k=1):
            pass
        assert profiler.metrics[0].operation_name == "aop"
        assert profiler.metrics[0].metadata == {"k": 1}

    def test_memory_usage_and_failure(self, profiler):
        profiler._process = MagicMock()
        profiler._process.memory_info.return_value.rss = 5 * 1024 * 1024
        assert profiler._get_memory_usage() == 5.0
        profiler._process.memory_info.side_effect = RuntimeError("gone")
        assert profiler._get_memory_usage() == 0.0

    def test_summary_empty(self, profiler):
        assert profiler.get_metrics_summary() == {}

    def test_summary_mixed(self, profiler):
        with profiler.measure("a"):
            pass
        with pytest.raises(KeyError), profiler.measure("b"):
            raise KeyError("k")
        s = profiler.get_metrics_summary()
        assert s["total_operations"] == 2
        assert s["successful_operations"] == 1
        assert s["success_rate"] == 0.5
        assert s["errors"] == ["'k'"]
        assert s["avg_duration_ms"] > 0

    def test_summary_all_failed(self, profiler):
        with pytest.raises(ValueError), profiler.measure("a"):
            raise ValueError("x")
        s = profiler.get_metrics_summary()
        assert s["avg_duration_ms"] == 0
        assert s["p95_duration_ms"] == 0
        assert s["p99_duration_ms"] == 0

    def test_percentile(self, profiler):
        assert profiler._percentile([], 0.5) == 0.0
        assert profiler._percentile([3.0, 1.0, 2.0], 0.5) == 2.0
        assert profiler._percentile([1.0, 2.0], 1.0) == 2.0

    def test_reset(self, profiler):
        with profiler.measure("a"):
            pass
        profiler.reset()
        assert profiler.metrics == []


class TestProfileDecorator:
    def test_sync(self, mocker):
        log = mocker.patch.object(profiling, "logger")

        @profile_performance("custom", enable_memory=False)
        def add(a, b):
            """doc"""
            return a + b

        assert add(1, 2) == 3
        assert add.__name__ == "add"
        assert "Performance custom" in log.info.call_args.args[0]

    async def test_async_defaults_to_function_name(self, mocker):
        log = mocker.patch.object(profiling, "logger")

        @profile_performance(enable_memory=False)
        async def work(x):
            return x * 2

        assert await work(4) == 8
        assert "Performance work" in log.info.call_args.args[0]

    def test_sync_exception_propagates(self):
        @profile_performance(enable_memory=False)
        def boom():
            raise RuntimeError("x")

        with pytest.raises(RuntimeError):
            boom()


class TestBenchmarkSuite:
    async def test_sync_operation(self):
        suite = BenchmarkSuite()
        calls = []
        result = await suite.run_benchmark(
            "sync", lambda **kw: calls.append(kw), iterations=5, warmup_iterations=2, a=1
        )
        assert len(calls) == 7
        assert calls[0] == {"a": 1}
        assert isinstance(result, BenchmarkResult)
        assert result.total_operations == 5
        assert result.success_rate == 1.0
        assert result.errors == []
        assert suite.results == [result]

    async def test_async_operation(self):
        suite = BenchmarkSuite()
        count = {"n": 0}

        async def op():
            count["n"] += 1

        result = await suite.run_benchmark("async", op, iterations=3, warmup_iterations=1)
        assert count["n"] == 4
        assert result.success_rate == 1.0
        assert result.avg_latency_ms >= 0

    async def test_failures_recorded_and_limited(self):
        suite = BenchmarkSuite()

        def bad():
            raise ValueError("nope")

        result = await suite.run_benchmark("bad", bad, iterations=12, warmup_iterations=1)
        assert result.success_rate == 0
        assert result.avg_latency_ms == 0
        assert len(result.errors) == 10
        assert result.errors[0] == "Iteration 0: nope"

    async def test_zero_iterations(self):
        result = await BenchmarkSuite().run_benchmark(
            "none", lambda: None, iterations=0, warmup_iterations=0
        )
        assert result.success_rate == 0
        assert result.operations_per_second == 0

    async def test_restarts_tracemalloc_when_stopped(self, mocker):
        suite = BenchmarkSuite()
        mocker.patch.object(profiling.tracemalloc, "is_tracing", return_value=False)
        start = mocker.patch.object(profiling.tracemalloc, "start")
        await suite.run_benchmark("t", lambda: None, iterations=1, warmup_iterations=0)
        start.assert_called_once()

    def test_report_empty(self):
        assert BenchmarkSuite().get_summary_report() == "No benchmark results available."

    def test_report_with_results_and_errors(self):
        suite = BenchmarkSuite()
        suite.results.append(
            BenchmarkResult("s1", 10, 1.0, 10.0, 1.0, 2.0, 3.0, 0.5, 50.0, 0.9, ["e1", "e2"])
        )
        suite.results.append(BenchmarkResult("s2", 1, 1.0, 1.0, 1.0, 1.0, 1.0, 0.1, 1.0, 1.0))
        report = suite.get_summary_report()
        assert "Scenario: s1" in report
        assert "Scenario: s2" in report
        assert "Errors: 2" in report
        assert "    - e1" in report
        assert "Success Rate: 90.0%" in report
