"""
Comprehensive load testing scenarios for the Candles Feed framework.

This module provides load testing scenarios that can be run both locally
and in CI environments. It includes setup and teardown for mock servers
and comprehensive performance measurement.

Usage:
    python tests/load/test_load_scenarios.py
    # or
    pytest tests/load/test_load_scenarios.py -v
"""

import asyncio
import json
import logging
import time
from statistics import mean, median
from typing import Dict, List, Tuple

import aiohttp
import pytest

from candles_feed.mocking_resources.core.server import MockedExchangeServer
from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import (
    BinanceSpotPlugin,
)

logger = logging.getLogger(__name__)


class LoadTestMetrics:
    """Collect and analyze performance metrics during load testing."""

    def __init__(self):
        self.request_times: List[float] = []
        self.response_codes: List[int] = []
        self.errors: List[str] = []
        self.start_time: float = 0
        self.end_time: float = 0

    def record_request(self, response_time: float, status_code: int, error: str = None):
        """Record a single request's metrics."""
        self.request_times.append(response_time)
        self.response_codes.append(status_code)
        if error:
            self.errors.append(error)

    def start_test(self):
        """Mark the start of the load test."""
        self.start_time = time.time()

    def end_test(self):
        """Mark the end of the load test."""
        self.end_time = time.time()

    def get_summary(self) -> Dict:
        """Generate a comprehensive performance summary."""
        if not self.request_times:
            return {"error": "No requests recorded"}

        total_requests = len(self.request_times)
        duration = self.end_time - self.start_time if self.end_time > self.start_time else 1

        success_codes = [code for code in self.response_codes if 200 <= code < 300]
        error_codes = [code for code in self.response_codes if code >= 400]

        sorted_times = sorted(self.request_times)
        p95_index = int(0.95 * len(sorted_times))
        p99_index = int(0.99 * len(sorted_times))

        return {
            "total_requests": total_requests,
            "duration_seconds": round(duration, 2),
            "requests_per_second": round(total_requests / duration, 2),
            "success_rate": round(len(success_codes) / total_requests * 100, 2),
            "error_count": len(error_codes),
            "response_times": {
                "mean": round(mean(self.request_times), 2),
                "median": round(median(self.request_times), 2),
                "min": round(min(self.request_times), 2),
                "max": round(max(self.request_times), 2),
                "p95": round(sorted_times[p95_index], 2) if p95_index < len(sorted_times) else 0,
                "p99": round(sorted_times[p99_index], 2) if p99_index < len(sorted_times) else 0,
            },
            "errors": self.errors[:10],  # First 10 errors
        }


class CandlesFeedLoadTester:
    """Load tester for Candles Feed endpoints."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session: aiohttp.ClientSession = None
        self.metrics = LoadTestMetrics()

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, path: str, **kwargs) -> Tuple[float, int, str]:
        """Make a timed HTTP request and record metrics."""
        start_time = time.time()
        error_msg = None

        try:
            async with self.session.request(method, f"{self.base_url}{path}", **kwargs) as response:
                await response.read()  # Ensure full response is received
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                return response_time, response.status, error_msg
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            return response_time, 0, error_msg

    async def test_klines_endpoint(self, concurrent_users: int = 10, requests_per_user: int = 20):
        """Load test the klines (candle data) endpoint."""
        print(
            f"🔥 Load testing klines endpoint: {concurrent_users} users, {requests_per_user} requests each"
        )

        trading_pairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT"]
        intervals = ["1m", "5m", "15m", "30m"]

        async def user_scenario():
            """Simulate a single user's request pattern."""
            for _ in range(requests_per_user):
                # Vary the request parameters
                symbol = trading_pairs[hash(time.time()) % len(trading_pairs)]
                interval = intervals[hash(time.time() + 1) % len(intervals)]
                limit = [100, 200, 500][hash(time.time() + 2) % 3]

                params = {"symbol": symbol, "interval": interval, "limit": limit}
                response_time, status_code, error = await self._make_request(
                    "GET", "/api/v3/klines", params=params
                )
                self.metrics.record_request(response_time, status_code, error)

                # Brief pause between requests (realistic user behavior)
                await asyncio.sleep(0.1)

        # Run concurrent users
        self.metrics.start_test()
        tasks = [user_scenario() for _ in range(concurrent_users)]
        await asyncio.gather(*tasks)
        self.metrics.end_test()

    async def test_server_endpoints(self, concurrent_users: int = 5, requests_per_user: int = 10):
        """Load test basic server endpoints (ping, time, exchangeInfo)."""
        print(
            f"🔥 Load testing server endpoints: {concurrent_users} users, {requests_per_user} requests each"
        )

        endpoints = ["/api/v3/ping", "/api/v3/time", "/api/v3/exchangeInfo"]

        async def user_scenario():
            """Simulate a single user testing various endpoints."""
            for _ in range(requests_per_user):
                endpoint = endpoints[hash(time.time()) % len(endpoints)]
                response_time, status_code, error = await self._make_request("GET", endpoint)
                self.metrics.record_request(response_time, status_code, error)
                await asyncio.sleep(0.05)  # Shorter pause for lighter endpoints

        # Run concurrent users
        tasks = [user_scenario() for _ in range(concurrent_users)]
        await asyncio.gather(*tasks)

    async def mixed_workload_test(self, duration_seconds: int = 30):
        """Run a mixed workload test for a specified duration."""
        print(f"🔥 Running mixed workload test for {duration_seconds} seconds")

        end_time = time.time() + duration_seconds

        async def heavy_user():
            """User making frequent klines requests."""
            while time.time() < end_time:
                response_time, status_code, error = await self._make_request(
                    "GET",
                    "/api/v3/klines",
                    params={"symbol": "BTCUSDT", "interval": "1m", "limit": 100},
                )
                self.metrics.record_request(response_time, status_code, error)
                await asyncio.sleep(0.5)

        async def light_user():
            """User making occasional server info requests."""
            while time.time() < end_time:
                response_time, status_code, error = await self._make_request("GET", "/api/v3/time")
                self.metrics.record_request(response_time, status_code, error)
                await asyncio.sleep(2)

        # Mix of user types
        tasks = [heavy_user() for _ in range(3)] + [light_user() for _ in range(2)]
        await asyncio.gather(*tasks)


@pytest.fixture
async def mock_server():
    """Fixture to provide a mock exchange server for load testing."""
    plugin = BinanceSpotPlugin()
    server = MockedExchangeServer(plugin, "127.0.0.1", 8791)

    # Add trading pairs with all intervals needed for testing
    trading_pairs = [
        ("BTCUSDT", 50000.0),
        ("ETHUSDT", 3000.0),
        ("BNBUSDT", 400.0),
        ("ADAUSDT", 1.0),
    ]
    intervals = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

    for symbol, price in trading_pairs:
        for interval in intervals:
            server.add_trading_pair(symbol, interval, price)

    url = await server.start()
    yield url
    await server.stop()


@pytest.mark.asyncio
async def test_basic_load_klines(mock_server):
    """Test basic load on the klines endpoint."""
    async with CandlesFeedLoadTester(mock_server) as tester:
        await tester.test_klines_endpoint(concurrent_users=5, requests_per_user=10)

        summary = tester.metrics.get_summary()
        print("\n📊 Klines Load Test Results:")
        print(json.dumps(summary, indent=2))

        # Basic performance assertions
        assert summary["success_rate"] >= 95, f"Success rate too low: {summary['success_rate']}%"
        assert summary["response_times"]["mean"] < 1000, (
            f"Mean response time too high: {summary['response_times']['mean']}ms"
        )
        assert summary["requests_per_second"] > 10, f"RPS too low: {summary['requests_per_second']}"


@pytest.mark.asyncio
async def test_server_endpoints_load(mock_server):
    """Test load on basic server endpoints."""
    async with CandlesFeedLoadTester(mock_server) as tester:
        await tester.test_server_endpoints(concurrent_users=3, requests_per_user=15)

        summary = tester.metrics.get_summary()
        print("\n📊 Server Endpoints Load Test Results:")
        print(json.dumps(summary, indent=2))

        # Performance assertions for lighter endpoints
        assert summary["success_rate"] >= 98, f"Success rate too low: {summary['success_rate']}%"
        assert summary["response_times"]["mean"] < 500, (
            f"Mean response time too high: {summary['response_times']['mean']}ms"
        )


@pytest.mark.asyncio
async def test_mixed_workload(mock_server):
    """Test mixed workload scenario."""
    async with CandlesFeedLoadTester(mock_server) as tester:
        tester.metrics.start_test()
        await tester.mixed_workload_test(duration_seconds=15)
        tester.metrics.end_test()

        summary = tester.metrics.get_summary()
        print("\n📊 Mixed Workload Test Results:")
        print(json.dumps(summary, indent=2))

        # Assertions for mixed workload
        assert summary["success_rate"] >= 90, f"Success rate too low: {summary['success_rate']}%"
        assert summary["error_count"] <= 5, f"Too many errors: {summary['error_count']}"


if __name__ == "__main__":
    """Run load tests directly when executed as a script."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "standalone":
        # Standalone mode - start server and run tests
        async def run_standalone_tests():
            plugin = BinanceSpotPlugin()
            server = MockedExchangeServer(plugin, "127.0.0.1", 8791)

            # Add trading pairs with multiple intervals for comprehensive testing
            trading_pairs = [("BTCUSDT", 50000.0), ("ETHUSDT", 3000.0)]
            intervals = ["1m", "5m", "15m", "30m", "1h"]

            for symbol, price in trading_pairs:
                for interval in intervals:
                    server.add_trading_pair(symbol, interval, price)

            url = await server.start()
            print(f"🚀 Mock server started at {url}")

            try:
                async with CandlesFeedLoadTester(url) as tester:
                    print("\n=== Running Basic Klines Load Test ===")
                    await tester.test_klines_endpoint(concurrent_users=10, requests_per_user=20)
                    print(json.dumps(tester.metrics.get_summary(), indent=2))

                    # Reset metrics for next test
                    tester.metrics = LoadTestMetrics()

                    print("\n=== Running Mixed Workload Test ===")
                    tester.metrics.start_test()
                    await tester.mixed_workload_test(duration_seconds=30)
                    tester.metrics.end_test()
                    print(json.dumps(tester.metrics.get_summary(), indent=2))

            finally:
                await server.stop()
                print("🛑 Mock server stopped")

        asyncio.run(run_standalone_tests())
    else:
        print("Run with pytest: pytest tests/load/test_load_scenarios.py -v")
        print("Or standalone mode: python tests/load/test_load_scenarios.py standalone")
