"""
Performance profiling utilities for the Candles Feed framework.

This module provides decorators, context managers, and benchmarking tools
for measuring and optimizing performance.
"""

import asyncio
import functools
import gc
import logging
import time
import tracemalloc
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar

import psutil

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""

    operation_name: str
    duration_ms: float
    memory_peak_mb: float
    memory_current_mb: float
    cpu_percent: float
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Container for benchmark test results."""

    scenario_name: str
    total_operations: int
    duration_seconds: float
    operations_per_second: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    memory_peak_mb: float
    memory_final_mb: float
    success_rate: float
    errors: List[str] = field(default_factory=list)


class PerformanceProfiler:
    """Performance profiler for measuring operation characteristics."""

    def __init__(self, enable_memory_tracking: bool = True):
        """Initialize the profiler.

        :param enable_memory_tracking: Whether to track memory usage
        """
        self.enable_memory_tracking = enable_memory_tracking
        self.metrics: List[PerformanceMetrics] = []
        self._start_memory = 0
        self._process = psutil.Process()

        if enable_memory_tracking:
            tracemalloc.start()

    @contextmanager
    def measure(self, operation_name: str, **metadata):
        """Context manager for measuring operation performance.

        :param operation_name: Name of the operation being measured
        :param metadata: Additional metadata to record
        """
        start_time = time.perf_counter()
        start_memory = 0
        peak_memory = 0

        if self.enable_memory_tracking:
            start_memory = self._get_memory_usage()

        cpu_start = self._process.cpu_percent()

        try:
            yield
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000

            current_memory = 0
            if self.enable_memory_tracking:
                current_memory = self._get_memory_usage()
                peak_memory = max(start_memory, current_memory)

            cpu_end = self._process.cpu_percent()
            cpu_percent = max(cpu_start, cpu_end)

            metrics = PerformanceMetrics(
                operation_name=operation_name,
                duration_ms=duration_ms,
                memory_peak_mb=peak_memory,
                memory_current_mb=current_memory,
                cpu_percent=cpu_percent,
                success=success,
                error=error,
                metadata=metadata,
            )

            self.metrics.append(metrics)

            logger.debug(
                f"Performance: {operation_name} took {duration_ms:.2f}ms, "
                f"memory: {current_memory:.1f}MB, cpu: {cpu_percent:.1f}%"
            )

    @asynccontextmanager
    async def measure_async(self, operation_name: str, **metadata):
        """Async context manager for measuring operation performance.

        :param operation_name: Name of the operation being measured
        :param metadata: Additional metadata to record
        """
        with self.measure(operation_name, **metadata):
            yield

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            memory_info = self._process.memory_info()
            return memory_info.rss / 1024 / 1024
        except Exception:
            return 0.0

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all recorded metrics."""
        if not self.metrics:
            return {}

        durations = [m.duration_ms for m in self.metrics if m.success]
        memory_peaks = [m.memory_peak_mb for m in self.metrics]

        return {
            "total_operations": len(self.metrics),
            "successful_operations": len(durations),
            "success_rate": len(durations) / len(self.metrics) if self.metrics else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "p95_duration_ms": self._percentile(durations, 0.95) if durations else 0,
            "p99_duration_ms": self._percentile(durations, 0.99) if durations else 0,
            "peak_memory_mb": max(memory_peaks) if memory_peaks else 0,
            "final_memory_mb": memory_peaks[-1] if memory_peaks else 0,
            "errors": [m.error for m in self.metrics if not m.success],
        }

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def reset(self):
        """Reset all collected metrics."""
        self.metrics.clear()
        gc.collect()


def profile_performance(operation_name: str = None, enable_memory: bool = True):
    """Decorator for profiling function performance.

    :param operation_name: Name for the operation (defaults to function name)
    :param enable_memory: Whether to track memory usage
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = PerformanceProfiler(enable_memory_tracking=enable_memory)
            name = operation_name or func.__name__

            with profiler.measure(name):
                result = func(*args, **kwargs)

            # Log performance metrics
            summary = profiler.get_metrics_summary()
            logger.info(
                f"Performance {name}: {summary['avg_duration_ms']:.2f}ms, "
                f"memory: {summary['peak_memory_mb']:.1f}MB"
            )

            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            profiler = PerformanceProfiler(enable_memory_tracking=enable_memory)
            name = operation_name or func.__name__

            async with profiler.measure_async(name):
                result = await func(*args, **kwargs)

            # Log performance metrics
            summary = profiler.get_metrics_summary()
            logger.info(
                f"Performance {name}: {summary['avg_duration_ms']:.2f}ms, "
                f"memory: {summary['peak_memory_mb']:.1f}MB"
            )

            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper

    return decorator


class BenchmarkSuite:
    """Benchmark test suite for performance testing."""

    def __init__(self):
        """Initialize the benchmark suite."""
        self.results: List[BenchmarkResult] = []
        self.profiler = PerformanceProfiler()

    async def run_benchmark(
        self,
        scenario_name: str,
        operation_func: Callable,
        iterations: int = 100,
        warmup_iterations: int = 10,
        **operation_kwargs,
    ) -> BenchmarkResult:
        """Run a benchmark scenario.

        :param scenario_name: Name of the benchmark scenario
        :param operation_func: Function to benchmark
        :param iterations: Number of iterations to run
        :param warmup_iterations: Number of warmup iterations
        :param operation_kwargs: Keyword arguments for the operation function
        :return: Benchmark results
        """
        logger.info(f"Starting benchmark: {scenario_name}")

        # Warmup
        logger.debug(f"Running {warmup_iterations} warmup iterations")
        for _ in range(warmup_iterations):
            try:
                if asyncio.iscoroutinefunction(operation_func):
                    await operation_func(**operation_kwargs)
                else:
                    operation_func(**operation_kwargs)
            except Exception as e:
                logger.warning(f"Warmup iteration failed: {e}")

        # Reset metrics after warmup
        self.profiler.reset()
        gc.collect()

        # Actual benchmark
        start_time = time.perf_counter()
        start_memory = self.profiler._get_memory_usage()
        errors = []

        for i in range(iterations):
            try:
                with self.profiler.measure(f"{scenario_name}_iteration_{i}"):
                    if asyncio.iscoroutinefunction(operation_func):
                        await operation_func(**operation_kwargs)
                    else:
                        operation_func(**operation_kwargs)
            except Exception as e:
                error_msg = f"Iteration {i}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)

        end_time = time.perf_counter()
        total_duration = end_time - start_time
        final_memory = self.profiler._get_memory_usage()

        # Calculate statistics
        successful_metrics = [m for m in self.profiler.metrics if m.success]
        durations = [m.duration_ms for m in successful_metrics]

        result = BenchmarkResult(
            scenario_name=scenario_name,
            total_operations=iterations,
            duration_seconds=total_duration,
            operations_per_second=len(successful_metrics) / total_duration
            if total_duration > 0
            else 0,
            avg_latency_ms=sum(durations) / len(durations) if durations else 0,
            p95_latency_ms=self.profiler._percentile(durations, 0.95),
            p99_latency_ms=self.profiler._percentile(durations, 0.99),
            memory_peak_mb=max(
                [m.memory_peak_mb for m in self.profiler.metrics], default=start_memory
            ),
            memory_final_mb=final_memory,
            success_rate=len(successful_metrics) / iterations if iterations > 0 else 0,
            errors=errors[:10],  # Limit to first 10 errors
        )

        self.results.append(result)

        logger.info(
            f"Benchmark {scenario_name} completed: "
            f"{result.operations_per_second:.1f} ops/s, "
            f"avg latency: {result.avg_latency_ms:.2f}ms, "
            f"p95: {result.p95_latency_ms:.2f}ms, "
            f"success rate: {result.success_rate:.1%}"
        )

        return result

    def get_summary_report(self) -> str:
        """Generate a summary report of all benchmark results."""
        if not self.results:
            return "No benchmark results available."

        report = ["Performance Benchmark Summary", "=" * 50]

        for result in self.results:
            report.extend(
                [
                    f"\nScenario: {result.scenario_name}",
                    f"  Operations: {result.total_operations}",
                    f"  Duration: {result.duration_seconds:.2f}s",
                    f"  Throughput: {result.operations_per_second:.1f} ops/s",
                    f"  Avg Latency: {result.avg_latency_ms:.2f}ms",
                    f"  P95 Latency: {result.p95_latency_ms:.2f}ms",
                    f"  P99 Latency: {result.p99_latency_ms:.2f}ms",
                    f"  Memory Peak: {result.memory_peak_mb:.1f}MB",
                    f"  Success Rate: {result.success_rate:.1%}",
                ]
            )

            if result.errors:
                report.append(f"  Errors: {len(result.errors)} (showing first few)")
                for error in result.errors[:3]:
                    report.append(f"    - {error}")

        return "\n".join(report)


# Global profiler instance for convenience
default_profiler = PerformanceProfiler()
