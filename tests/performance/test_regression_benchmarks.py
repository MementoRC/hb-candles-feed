"""
Performance regression tests using pytest-benchmark.

These tests establish performance baselines and detect regressions
across core functionality of the candles-feed framework.
"""

import time

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.metrics import MetricsCollector, PerformanceTracker
from candles_feed.core.monitoring import MonitoringConfig
from candles_feed.core.network_client import NetworkClient
from candles_feed.mocking_resources.adapter.mocked_adapter import MockedAdapter


class TestCandleDataBenchmarks:
    """Benchmark tests for CandleData operations."""

    def test_candle_creation_benchmark(self, benchmark):
        """Benchmark CandleData creation performance."""

        def create_candle():
            return CandleData(
                timestamp_raw=1609459200,
                open=50000.0,
                high=51000.0,
                low=49500.0,
                close=50500.0,
                volume=1000.0,
            )

        result = benchmark(create_candle)
        assert result.timestamp == 1609459200

    def test_candle_normalization_benchmark(self, benchmark):
        """Benchmark timestamp normalization performance."""

        def normalize_timestamp():
            # Test various timestamp formats
            timestamps = [
                1609459200,  # seconds
                1609459200000,  # milliseconds
                1609459200000000,  # microseconds
                "2021-01-01T00:00:00Z",  # ISO string
            ]
            return [CandleData._normalize_timestamp(ts) for ts in timestamps]

        result = benchmark(normalize_timestamp)
        assert len(result) == 4
        assert all(isinstance(ts, int) for ts in result)

    def test_candle_array_conversion_benchmark(self, benchmark):
        """Benchmark CandleData array conversion performance."""
        candle = CandleData(
            timestamp_raw=1609459200,
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
        )

        def convert_to_array():
            return candle.to_array()

        result = benchmark(convert_to_array)
        assert len(result) == 10


class TestDataProcessorBenchmarks:
    """Benchmark tests for DataProcessor operations."""

    def test_candle_sanitization_benchmark(self, benchmark):
        """Benchmark candle sanitization performance."""
        processor = DataProcessor()

        # Create test candles with some gaps and inconsistencies
        candles = []
        for i in range(300):
            candle = CandleData(
                timestamp_raw=1609459200 + i * 60,  # 1 minute intervals
                open=50000.0 + i * 0.1,
                high=50050.0 + i * 0.1,
                low=49950.0 + i * 0.1,
                close=50025.0 + i * 0.1,
                volume=1000.0 + i,
            )
            candles.append(candle)

        def sanitize_candles():
            return processor.sanitize_candles(candles, 60)  # 60 seconds interval

        result = benchmark(sanitize_candles)
        assert len(result) <= 300
        assert all(isinstance(candle, CandleData) for candle in result)


class TestNetworkClientBenchmarks:
    """Benchmark tests for NetworkClient operations."""

    def test_connection_creation_benchmark(self, benchmark):
        """Benchmark network client connection setup."""

        def create_client():
            return NetworkClient()

        client = benchmark(create_client)
        assert client is not None

    def test_connection_pool_stats_benchmark(self, benchmark):
        """Benchmark connection pool statistics retrieval."""
        client = NetworkClient()

        def get_stats():
            return client.get_connection_pool_stats()

        result = benchmark(get_stats)
        assert isinstance(result, dict)


class TestMetricsBenchmarks:
    """Benchmark tests for metrics collection performance."""

    def test_metrics_collection_benchmark(self, benchmark):
        """Benchmark metrics collection operations."""

        def collect_metrics():
            # Disable logging for this specific benchmark to avoid excessive output
            config = MonitoringConfig(enable_structured_logging=False)
            collector = MetricsCollector(monitoring_manager=None)  # Use default manager
            collector.monitoring.config = config  # Apply the custom config

            # Simulate typical metrics collection workload
            for i in range(100):
                collector.record_request_started("GET", f"/api/v1/klines?symbol=BTC{i}")
                collector.record_request_completed(
                    0.1, True, "GET", f"/api/v1/klines?symbol=BTC{i}"
                )
                collector.record_candles_processed(10, "binance")
            return collector

        result_collector = benchmark(collect_metrics)
        assert result_collector.metrics.total_requests == 100
        assert result_collector.metrics.candles_processed == 1000

    def test_performance_tracker_benchmark(self, benchmark):
        """Benchmark performance tracker context managers."""

        def track_operations():
            # Create fresh tracker for each benchmark run
            tracker = PerformanceTracker()
            # Simulate tracking 50 operations
            for i in range(50):
                with tracker.track_request("GET", f"/api/endpoint/{i}"):
                    time.sleep(0.001)  # Simulate small work
            return tracker

        result_tracker = benchmark(track_operations)
        assert result_tracker.collector.metrics.total_requests == 50


class TestAdapterBenchmarks:
    """Benchmark tests for adapter operations."""

    def test_adapter_initialization_benchmark(self, benchmark):
        """Benchmark adapter creation and setup."""

        def create_adapter():
            return MockedAdapter()

        adapter = benchmark(create_adapter)
        assert adapter is not None


class TestIntegrationBenchmarks:
    """Benchmark tests for integrated operations."""

    def test_concurrent_operations_benchmark(self, benchmark):
        """Benchmark concurrent operations performance."""

        def concurrent_metrics_collection():
            collectors = [MetricsCollector() for _ in range(10)]

            # Simulate concurrent metrics collection
            for collector in collectors:
                for _i in range(20):
                    collector.record_request_started()
                    collector.record_request_completed(0.05, True)

            return sum(c.metrics.total_requests for c in collectors)

        result = benchmark(concurrent_metrics_collection)
        assert result == 200  # 10 collectors * 20 requests each


@pytest.mark.benchmark
class TestPerformanceRegression:
    """Performance regression detection tests."""

    def test_memory_usage_candle_creation(self, benchmark):
        """Track memory usage for candle creation to detect memory leaks."""
        import tracemalloc

        def create_many_candles():
            tracemalloc.start()
            candles = []
            for _i in range(1000):
                candle = CandleData(
                    timestamp_raw=1609459200 + _i * 60,
                    open=50000.0 + _i,
                    high=51000.0 + _i,
                    low=49500.0 + _i,
                    close=50500.0 + _i,
                    volume=1000.0,
                )
                candles.append(candle)

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            return len(candles), peak

        count, peak_memory = benchmark(create_many_candles)
        assert count == 1000
        # Peak memory should be reasonable (less than 50MB for 1000 candles)
        assert peak_memory < 50 * 1024 * 1024

    def test_cpu_intensive_operations(self, benchmark):
        """Benchmark CPU-intensive operations for performance tracking."""
        processor = DataProcessor()

        # Create large dataset of candles
        candles = []
        for i in range(10000):
            candle = CandleData(
                timestamp_raw=1609459200 + i * 60,  # timestamp
                open=50000 + i * 0.1,  # open
                high=50050 + i * 0.1,  # high
                low=49950 + i * 0.1,  # low
                close=50025 + i * 0.1,  # close
                volume=1000 + i * 0.01,  # volume
            )
            candles.append(candle)

        def process_large_dataset():
            return processor.sanitize_candles(candles, 60)

        result = benchmark(process_large_dataset)
        assert len(result) <= 10000
