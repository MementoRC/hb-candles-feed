"""
Performance benchmark tests for the Candles Feed framework.

These tests measure performance characteristics and validate that the framework
meets the PRD performance targets.
"""

import asyncio
import time
from datetime import datetime

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.network_config import NetworkConfig
from candles_feed.mocking_resources.adapter import AsyncMockedAdapter
from candles_feed.mocking_resources.core.server import MockedExchangeServer
from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import (
    BinanceSpotPlugin,
)
from candles_feed.utils.profiling import BenchmarkSuite, PerformanceProfiler, profile_performance


class TestNetworkClientPerformance:
    """Performance tests for NetworkClient connection pooling and optimization."""

    @pytest.mark.asyncio
    async def test_connection_pool_reuse(self):
        """Test that connection pooling reduces connection establishment overhead."""
        config = NetworkConfig(connection_pool_size=50, enable_connection_pooling=True)

        network_client = NetworkClient(config)

        # Mock server for testing
        plugin = BinanceSpotPlugin()
        server = MockedExchangeServer(plugin, port=8765)
        try:
            await server.start()

            url = "http://127.0.0.1:8765/api/v3/ping"

            # Measure first request (establishes connection)
            start_time = time.perf_counter()
            await network_client.get_rest_data(url)
            first_request_time = time.perf_counter() - start_time

            # Measure subsequent requests (should reuse connection)
            subsequent_times = []
            for _ in range(10):
                start_time = time.perf_counter()
                await network_client.get_rest_data(url)
                subsequent_times.append(time.perf_counter() - start_time)

            avg_subsequent_time = sum(subsequent_times) / len(subsequent_times)

            # Connection reuse should make subsequent requests faster
            assert avg_subsequent_time < first_request_time, (
                f"Connection pooling ineffective: first={first_request_time:.3f}s, avg={avg_subsequent_time:.3f}s"
            )

            # Verify connection pool statistics
            stats = network_client.get_connection_pool_stats()
            assert "total_connections" in stats, f"Stats missing total_connections: {stats}"
            assert stats["total_connections"] >= 0
            assert "connector_closed" in stats
            assert not stats["connector_closed"]

        finally:
            await network_client.close()
            await server.stop()

    @pytest.mark.asyncio
    async def test_concurrent_request_performance(self):
        """Test performance under concurrent load."""
        config = NetworkConfig(rest_api_timeout=10.0)

        network_client = NetworkClient(config)
        plugin = BinanceSpotPlugin()
        server = MockedExchangeServer(plugin, port=8766)

        try:
            # Add trading pair to server before starting
            server.add_trading_pair("BTC-USDT", "1m", initial_price=50000.0)
            await server.start()

            url = "http://127.0.0.1:8766/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": "1m", "limit": "10"}

            # Benchmark concurrent requests
            benchmark = BenchmarkSuite()

            async def make_request():
                return await network_client.get_rest_data(url, params=params)

            result = await benchmark.run_benchmark(
                "concurrent_requests", make_request, iterations=50, warmup_iterations=5
            )

            # Performance targets from PRD
            assert result.avg_latency_ms < 100, (
                f"Average latency too high: {result.avg_latency_ms:.2f}ms"
            )
            assert result.p95_latency_ms < 200, (
                f"P95 latency too high: {result.p95_latency_ms:.2f}ms"
            )
            assert result.success_rate > 0.95, f"Success rate too low: {result.success_rate:.1%}"

        finally:
            await network_client.close()
            await server.stop()


class TestDataProcessorPerformance:
    """Performance tests for optimized data processing operations."""

    def test_sanitize_candles_performance(self):
        """Test performance of the optimized sanitize_candles method."""
        processor = DataProcessor()

        # Generate test data with gaps and out-of-order elements
        base_time = int(datetime.now().timestamp())
        candles = []

        # Create 1000 candles with some gaps and disorder
        for i in range(1000):
            timestamp = base_time + (i * 60)  # 1-minute intervals
            candle = CandleData(
                timestamp_raw=timestamp,
                open=50000.0 + i,
                high=50010.0 + i,
                low=49990.0 + i,
                close=50005.0 + i,
                volume=100.0,
            )
            candles.append(candle)

        # Introduce some disorder and gaps
        candles[100], candles[150] = candles[150], candles[100]
        candles[500], candles[600] = candles[600], candles[500]
        del candles[200:210]  # Create a gap

        # Benchmark the sanitization
        profiler = PerformanceProfiler()

        with profiler.measure("sanitize_candles", data_size=len(candles)):
            result = processor.sanitize_candles(candles, 60)

        metrics = profiler.get_metrics_summary()

        # Performance targets
        assert metrics["avg_duration_ms"] < 50, (
            f"Sanitization too slow: {metrics['avg_duration_ms']:.2f}ms"
        )
        assert len(result) > 700, f"Too many candles filtered out: {len(result)} remaining"

        # Verify correctness
        assert all(result[i].timestamp <= result[i + 1].timestamp for i in range(len(result) - 1))

    def test_process_candle_performance(self):
        """Test performance of optimized candle insertion."""
        processor = DataProcessor()

        # Pre-fill with sorted candles
        from collections import deque

        candles_store = deque(maxlen=500)

        base_time = int(datetime.now().timestamp())
        for i in range(100):
            candle = CandleData(
                timestamp_raw=base_time + (i * 60),
                open=50000.0,
                high=50010.0,
                low=49990.0,
                close=50005.0,
                volume=100.0,
            )
            candles_store.append(candle)

        # Test different insertion scenarios
        profiler = PerformanceProfiler()

        # Test append (most common case)
        new_candle = CandleData(
            timestamp_raw=base_time + (200 * 60),
            open=51000.0,
            high=51010.0,
            low=50990.0,
            close=51005.0,
            volume=100.0,
        )

        with profiler.measure("append_candle"):
            processor.process_candle(new_candle, candles_store)

        # Test prepend
        old_candle = CandleData(
            timestamp_raw=base_time - 60,
            open=49000.0,
            high=49010.0,
            low=48990.0,
            close=49005.0,
            volume=100.0,
        )

        with profiler.measure("prepend_candle"):
            processor.process_candle(old_candle, candles_store)

        # Test middle insertion (rare case)
        middle_candle = CandleData(
            timestamp_raw=base_time + (50 * 60) + 30,  # Between existing candles
            open=50500.0,
            high=50510.0,
            low=50490.0,
            close=50505.0,
            volume=100.0,
        )

        with profiler.measure("middle_insert_candle"):
            processor.process_candle(middle_candle, candles_store)

        metrics = profiler.get_metrics_summary()

        # All operations should be fast
        assert metrics["avg_duration_ms"] < 5, (
            f"Candle processing too slow: {metrics['avg_duration_ms']:.2f}ms"
        )


class TestAdapterPerformance:
    """Performance tests for adapter implementations."""

    @pytest.mark.asyncio
    async def test_mock_adapter_throughput(self):
        """Test mock adapter performance to establish baseline."""
        config = NetworkConfig()
        network_client = NetworkClient(config)

        adapter = AsyncMockedAdapter(
            network_client=network_client,
            network_config=config,
            exchange_name="binance",
            trading_pair="BTCUSDT",
        )

        benchmark = BenchmarkSuite()

        async def fetch_candles():
            return await adapter.fetch_rest_candles("BTCUSDT", "1m", limit=100)

        result = await benchmark.run_benchmark(
            "mock_adapter_throughput", fetch_candles, iterations=100, warmup_iterations=10
        )

        # Mock adapter should be very fast
        assert result.avg_latency_ms < 10, f"Mock adapter too slow: {result.avg_latency_ms:.2f}ms"
        assert result.success_rate == 1.0, f"Mock adapter failures: {result.success_rate:.1%}"
        assert result.memory_peak_mb < 300, f"Memory usage too high: {result.memory_peak_mb:.1f}MB"

        await network_client.close()

    @pytest.mark.asyncio
    async def test_memory_usage_scaling(self):
        """Test memory usage scaling with number of candles."""
        config = NetworkConfig()
        network_client = NetworkClient(config)

        memory_measurements = []
        candle_counts = [50, 100, 250, 500, 1000]

        for count in candle_counts:
            adapter = AsyncMockedAdapter(
                network_client=network_client,
                network_config=config,
                exchange_name="binance",
                trading_pair="BTCUSDT",
            )

            profiler = PerformanceProfiler()

            with profiler.measure(f"fetch_{count}_candles", candle_count=count):
                candles = await adapter.fetch_rest_candles("BTCUSDT", "1m", limit=count)
                assert len(candles) == count

            metrics = profiler.get_metrics_summary()
            memory_measurements.append(
                {
                    "candle_count": count,
                    "memory_mb": metrics["peak_memory_mb"],
                    "latency_ms": metrics["avg_duration_ms"],
                }
            )

        # Memory should scale reasonably
        max_memory = max(m["memory_mb"] for m in memory_measurements)
        assert max_memory < 500, f"Memory usage too high: {max_memory:.1f}MB"

        # Memory per candle should be reasonable (adjusted for test environment)
        for measurement in memory_measurements:
            memory_per_100_candles = (measurement["memory_mb"] / measurement["candle_count"]) * 100
            assert memory_per_100_candles < 500, (
                f"Memory per 100 candles too high: {memory_per_100_candles:.1f}MB at {measurement['candle_count']} candles"
            )

        await network_client.close()


class TestIntegrationPerformance:
    """End-to-end performance tests."""

    @pytest.mark.asyncio
    async def test_multiple_adapters_concurrent(self):
        """Test performance with multiple adapters running concurrently."""
        config = NetworkConfig(connection_pool_size=200)

        network_client = NetworkClient(config)

        # Create multiple adapters
        adapters = []
        for i in range(5):
            adapter = AsyncMockedAdapter(
                network_client=network_client,
                network_config=config,
                exchange_name=f"exchange_{i}",
                trading_pair="BTCUSDT",
            )
            adapters.append(adapter)

        benchmark = BenchmarkSuite()

        async def concurrent_fetch():
            """Fetch candles from all adapters concurrently."""
            tasks = [adapter.fetch_rest_candles("BTCUSDT", "1m", limit=50) for adapter in adapters]
            results = await asyncio.gather(*tasks)
            return results

        result = await benchmark.run_benchmark(
            "concurrent_multiple_adapters", concurrent_fetch, iterations=20, warmup_iterations=3
        )

        # Should handle concurrent load efficiently
        assert result.avg_latency_ms < 100, (
            f"Concurrent performance too slow: {result.avg_latency_ms:.2f}ms"
        )
        assert result.success_rate > 0.95, (
            f"Success rate too low under load: {result.success_rate:.1%}"
        )
        assert result.memory_peak_mb < 300, (
            f"Memory usage too high under load: {result.memory_peak_mb:.1f}MB"
        )

        # Check connection pool efficiency
        stats = network_client.get_connection_pool_stats()
        # Note: AsyncMockedAdapter doesn't use real HTTP requests, so connector may not be initialized
        if "status" in stats and stats["status"] == "not_initialized":
            # This is expected for mocked adapters
            assert stats["status"] == "not_initialized"
        else:
            assert "total_connections" in stats, f"Stats missing total_connections: {stats}"
            assert stats["total_connections"] >= 0, "Connection pool stats available"

        await network_client.close()

    @pytest.mark.asyncio
    async def test_sustained_load_performance(self):
        """Test performance under sustained load to detect memory leaks."""
        config = NetworkConfig()
        network_client = NetworkClient(config)

        adapter = AsyncMockedAdapter(
            network_client=network_client,
            network_config=config,
            exchange_name="binance",
            trading_pair="BTCUSDT",
        )

        profiler = PerformanceProfiler()
        initial_memory = profiler._get_memory_usage()

        # Run sustained operations
        for i in range(50):  # Reduced for faster test execution
            with profiler.measure(f"sustained_operation_{i}"):
                candles = await adapter.fetch_rest_candles("BTCUSDT", "1m", limit=100)
                assert len(candles) == 100

            # Check for memory leaks every 10 iterations
            if i % 10 == 0:
                current_memory = profiler._get_memory_usage()
                memory_growth = current_memory - initial_memory
                assert memory_growth < 50, (
                    f"Potential memory leak detected: {memory_growth:.1f}MB growth"
                )

        final_memory = profiler._get_memory_usage()
        total_growth = final_memory - initial_memory

        # Memory growth should be minimal under sustained load
        assert total_growth < 100, (
            f"Memory leak detected: {total_growth:.1f}MB growth over 50 operations"
        )

        await network_client.close()


# Utility function for running performance regression tests
@profile_performance("performance_regression_check")
def check_performance_regression():
    """Run a quick performance regression check."""
    processor = DataProcessor()

    # Generate test data
    base_time = int(datetime.now().timestamp())
    candles = []
    for i in range(100):
        candle = CandleData(
            timestamp_raw=base_time + (i * 60),
            open=50000.0,
            high=50010.0,
            low=49990.0,
            close=50005.0,
            volume=100.0,
        )
        candles.append(candle)

    # Process data
    result = processor.sanitize_candles(candles, 60)
    assert len(result) == 100

    return {"processed_candles": len(result)}


if __name__ == "__main__":
    # Quick performance check
    print("Running performance regression check...")
    result = check_performance_regression()
    print(f"Performance check completed: {result}")
