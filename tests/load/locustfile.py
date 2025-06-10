"""
Load testing scenarios for the Candles Feed framework.

This module implements load testing scenarios using Locust to test
critical application endpoints and workflows under various load conditions.

Key scenarios:
1. REST API load testing for candle data retrieval
2. WebSocket connection load testing for real-time data
3. Mixed workload testing combining REST and WebSocket usage

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8791
"""

import json
import random
from datetime import datetime, timedelta

from locust import HttpUser, TaskSet, between, events, task
from locust.exception import RescheduleTask


class CandleDataTaskSet(TaskSet):
    """Task set for testing candle data retrieval endpoints."""

    # Common trading pairs for testing
    TRADING_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"]
    INTERVALS = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]

    def on_start(self):
        """Initialize user session with basic health check."""
        # Test server connectivity
        with self.client.get("/api/v3/ping", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Server ping failed")
                raise RescheduleTask()

    @task(3)
    def get_klines_recent(self):
        """Test recent candle data retrieval (most common scenario)."""
        symbol = random.choice(self.TRADING_PAIRS)
        interval = random.choice(self.INTERVALS[:4])  # Focus on shorter intervals
        limit = random.choice([100, 200, 500])  # Common limit values

        params = {"symbol": symbol, "interval": interval, "limit": limit}

        with self.client.get("/api/v3/klines", params=params, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        response.success()
                    else:
                        response.failure("Empty or invalid candle data")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def get_klines_historical(self):
        """Test historical candle data retrieval with time range."""
        symbol = random.choice(self.TRADING_PAIRS)
        interval = random.choice(self.INTERVALS)

        # Generate time range for last 24-48 hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=random.randint(24, 48))

        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
        }

        with self.client.get("/api/v3/klines", params=params, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        response.success()
                    else:
                        response.failure("Invalid candle data format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def get_exchange_info(self):
        """Test exchange information endpoint."""
        with self.client.get("/api/v3/exchangeInfo", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "symbols" in data and isinstance(data["symbols"], list):
                        response.success()
                    else:
                        response.failure("Invalid exchange info format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def get_server_time(self):
        """Test server time endpoint (lightweight health check)."""
        with self.client.get("/api/v3/time", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "serverTime" in data and isinstance(data["serverTime"], int):
                        response.success()
                    else:
                        response.failure("Invalid server time format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")


class WebSocketTaskSet(TaskSet):
    """Task set for testing WebSocket connections and real-time data."""

    TRADING_PAIRS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    INTERVALS = ["1m", "5m", "15m"]

    def on_start(self):
        """Initialize WebSocket connection testing."""
        # Note: WebSocket testing with Locust requires additional setup
        # This is a placeholder for WebSocket load testing scenarios
        pass

    @task(1)
    def simulate_websocket_connection(self):
        """Simulate WebSocket connection load by testing the endpoint availability."""
        # Since Locust's HttpUser doesn't natively support WebSocket,
        # we test the WebSocket endpoint availability as a proxy metric
        with self.client.get("/ws/stream", catch_response=True) as response:
            # This will likely return a method not allowed or upgrade required
            # which is expected behavior for WebSocket endpoints
            if response.status_code in [405, 426, 101]:
                response.success()
            else:
                response.failure(f"Unexpected WebSocket endpoint response: {response.status_code}")


class RESTAPIUser(HttpUser):
    """User class for REST API load testing."""

    tasks = [CandleDataTaskSet]
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    weight = 3  # Higher weight for REST API testing


class WebSocketUser(HttpUser):
    """User class for WebSocket load testing."""

    tasks = [WebSocketTaskSet]
    wait_time = between(2, 5)  # Longer wait time for WebSocket simulation
    weight = 1  # Lower weight for WebSocket testing


# Locust event handlers for enhanced reporting
@events.request.add_listener
def on_request(request_type: str, name: str, response_time: float, response_length: int, **kwargs):
    """Log performance metrics for analysis."""
    if response_time > 1000:  # Log slow requests (>1s)
        print(f"Slow request detected: {name} took {response_time:.2f}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize load test session."""
    print("🚀 Starting Candles Feed load testing...")
    print(f"Target host: {environment.host}")
    print("Key metrics to monitor:")
    print("- Average response time for /api/v3/klines")
    print("- Request throughput (RPS)")
    print("- Error rate across all endpoints")
    print("- 95th percentile response times")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Finalize load test session."""
    print("✅ Load testing completed")
    print("Check Locust web UI for detailed performance metrics")
    print("Key files generated:")
    print("- Load test report (if --html option used)")
    print("- CSV data files (if --csv option used)")
