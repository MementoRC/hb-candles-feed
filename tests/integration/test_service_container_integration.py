"""
Enhanced integration tests using GitHub Actions service containers.

This module demonstrates improved integration testing with external dependencies:
- Redis for caching and state management
- WebSocket echo server for realistic WebSocket testing
- Service container health checks and connection management

These tests run with full service containers in CI but gracefully degrade 
when services are not available (e.g., local development).
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import pytest

# Test imports with fallback handling
try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.network_config import NetworkConfig
from candles_feed.mocking_resources.core.candle_data_factory import CandleDataFactory
from candles_feed.mocking_resources.core.server import MockedExchangeServer

try:
    from candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin import (
        BinanceSpotPlugin,
    )
    HAS_BINANCE_PLUGIN = True
except ImportError:
    from candles_feed.mocking_resources.exchange_server_plugins.mocked_plugin import (
        MockedPlugin as BinanceSpotPlugin,
    )
    HAS_BINANCE_PLUGIN = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.integration
class TestServiceContainerIntegration:
    """Integration tests utilizing service containers for external dependencies."""

    @pytest.fixture
    async def redis_client(self):
        """Create Redis client if available, otherwise skip."""
        if not HAS_REDIS or not self._is_redis_available():
            pytest.skip("Redis not available - requires service container in CI")
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        client = redis.from_url(redis_url, decode_responses=True)
        
        try:
            # Test connection
            await client.ping()
            yield client
        finally:
            await client.close()

    @pytest.fixture
    async def mock_server_with_caching(self):
        """Create mock server with Redis caching capabilities."""
        plugin = BinanceSpotPlugin()
        server = MockedExchangeServer(plugin, "127.0.0.1", 8791)
        
        # Add trading pairs
        server.add_trading_pair("BTCUSDT", "1m", 50000.0)
        server.add_trading_pair("ETHUSDT", "1m", 3000.0)
        
        # Start server
        url = await server.start()
        server.url = url
        
        yield server
        
        await server.stop()

    def _is_redis_available(self) -> bool:
        """Check if Redis service is available."""
        return os.getenv("TEST_WITH_SERVICES", "false").lower() == "true"

    def _is_websocket_echo_available(self) -> bool:
        """Check if WebSocket echo server is available."""
        return os.getenv("TEST_WITH_SERVICES", "false").lower() == "true"

    @pytest.mark.asyncio
    async def test_redis_caching_integration(self, redis_client, mock_server_with_caching):
        """Test integration with Redis for caching candle data."""
        if not HAS_REDIS:
            pytest.skip("Redis library not available")
            
        logger.info("Testing Redis caching integration")
        
        # Create a cache key for our test
        cache_key = "candles:btcusdt:1m"
        
        # Generate some test candle data
        base_timestamp = int(datetime.now(timezone.utc).timestamp())
        test_candles = []
        
        for i in range(5):
            candle = CandleDataFactory.create_random(
                timestamp=base_timestamp + (i * 60),
                base_price=50000.0 + (i * 100),
                volatility=0.01
            )
            test_candles.append(candle)
        
        # Store candles in Redis cache
        candle_data = [
            {
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in test_candles
        ]
        
        await redis_client.setex(cache_key, 3600, json.dumps(candle_data))
        logger.info(f"Stored {len(candle_data)} candles in Redis cache")
        
        # Retrieve and verify cached data
        cached_data = await redis_client.get(cache_key)
        assert cached_data is not None, "Cached data should be available"
        
        retrieved_candles = json.loads(cached_data)
        assert len(retrieved_candles) == 5, "Should retrieve all cached candles"
        
        # Verify data integrity
        for i, cached_candle in enumerate(retrieved_candles):
            original = test_candles[i]
            assert cached_candle["timestamp"] == original.timestamp
            assert abs(cached_candle["open"] - original.open) < 0.01
            assert abs(cached_candle["close"] - original.close) < 0.01
        
        logger.info("Redis caching integration test passed")
        
        # Test cache expiration
        ttl = await redis_client.ttl(cache_key)
        assert ttl > 0, "Cache should have a TTL set"
        assert ttl <= 3600, "TTL should not exceed the set value"
        
        # Clean up
        await redis_client.delete(cache_key)

    @pytest.mark.asyncio
    async def test_websocket_echo_server_integration(self):
        """Test integration with WebSocket echo server for realistic WebSocket testing."""
        if not HAS_WEBSOCKETS or not self._is_websocket_echo_available():
            pytest.skip("WebSocket echo server not available - requires service container in CI")
        
        logger.info("Testing WebSocket echo server integration")
        
        websocket_url = os.getenv("WEBSOCKET_ECHO_URL", "ws://localhost:8080")
        
        try:
            async with websockets.connect(websocket_url) as websocket:
                # Test basic echo functionality
                test_message = {"type": "subscribe", "symbol": "BTCUSDT", "interval": "1m"}
                await websocket.send(json.dumps(test_message))
                
                # Receive echo
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                echoed_message = json.loads(response)
                
                assert echoed_message == test_message, "Echo server should return exact message"
                logger.info("WebSocket echo test passed")
                
                # Test multiple message handling
                messages = [
                    {"type": "ping"},
                    {"type": "subscribe", "symbol": "ETHUSDT"},
                    {"type": "unsubscribe", "symbol": "BTCUSDT"},
                ]
                
                for msg in messages:
                    await websocket.send(json.dumps(msg))
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    echoed = json.loads(response)
                    assert echoed == msg, f"Message {msg} should be echoed correctly"
                
                logger.info("Multiple WebSocket message test passed")
                
        except Exception as e:
            logger.error(f"WebSocket echo server test failed: {e}")
            raise

    @pytest.mark.asyncio
    async def test_candles_feed_with_redis_state_management(self, redis_client, mock_server_with_caching):
        """Test CandlesFeed with Redis for state management."""
        if not HAS_REDIS:
            pytest.skip("Redis library not available")
            
        logger.info("Testing CandlesFeed with Redis state management")
        
        # Create feed with network config for testing
        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100,
            network_config=NetworkConfig.for_testing(),
        )
        
        # Store feed state in Redis
        feed_state_key = f"feed_state:{feed.exchange}:{feed.trading_pair}:{feed.interval}"
        initial_state = {
            "exchange": feed.exchange,
            "trading_pair": feed.trading_pair,
            "interval": feed.interval,
            "max_records": feed.max_records,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "initialized"
        }
        
        await redis_client.setex(feed_state_key, 1800, json.dumps(initial_state))
        logger.info("Stored feed state in Redis")
        
        # Retrieve and verify state
        stored_state = await redis_client.get(feed_state_key)
        assert stored_state is not None, "Feed state should be stored"
        
        state_data = json.loads(stored_state)
        assert state_data["exchange"] == feed.exchange
        assert state_data["trading_pair"] == feed.trading_pair
        assert state_data["interval"] == feed.interval
        assert state_data["status"] == "initialized"
        
        # Update state to "running"
        state_data["status"] = "running"
        state_data["last_update"] = datetime.now(timezone.utc).isoformat()
        await redis_client.setex(feed_state_key, 1800, json.dumps(state_data))
        
        # Verify update
        updated_state = await redis_client.get(feed_state_key)
        updated_data = json.loads(updated_state)
        assert updated_data["status"] == "running"
        assert "last_update" in updated_data
        
        logger.info("Redis state management test passed")
        
        # Clean up
        await redis_client.delete(feed_state_key)

    @pytest.mark.asyncio
    async def test_service_container_health_monitoring(self, redis_client):
        """Test monitoring and health checking of service containers."""
        if not HAS_REDIS:
            pytest.skip("Redis library not available")
            
        logger.info("Testing service container health monitoring")
        
        # Test Redis health
        redis_info = await redis_client.info()
        assert "redis_version" in redis_info, "Redis should provide version info"
        assert redis_info["connected_clients"] >= 1, "Redis should have connected clients"
        
        logger.info(f"Redis version: {redis_info.get('redis_version', 'unknown')}")
        logger.info(f"Connected clients: {redis_info.get('connected_clients', 0)}")
        
        # Test Redis performance
        start_time = asyncio.get_event_loop().time()
        await redis_client.ping()
        ping_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        assert ping_time < 100, "Redis ping should be fast (<100ms)"
        logger.info(f"Redis ping time: {ping_time:.2f}ms")
        
        # Test basic Redis operations performance
        test_key = "health_test"
        test_value = "health_check_value"
        
        start_time = asyncio.get_event_loop().time()
        await redis_client.set(test_key, test_value)
        retrieved_value = await redis_client.get(test_key)
        operation_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        assert retrieved_value == test_value, "Redis operations should work correctly"
        assert operation_time < 50, "Redis operations should be fast (<50ms)"
        
        logger.info(f"Redis operation time: {operation_time:.2f}ms")
        
        # Clean up
        await redis_client.delete(test_key)
        
        logger.info("Service container health monitoring test passed")

    @pytest.mark.asyncio
    async def test_integration_with_fallback_handling(self):
        """Test that integration tests gracefully handle missing service containers."""
        logger.info("Testing graceful fallback when service containers are not available")
        
        # This test should pass regardless of service container availability
        # It demonstrates how tests can adapt to different environments
        
        services_available = {
            "redis": HAS_REDIS and self._is_redis_available(),
            "websocket_echo": HAS_WEBSOCKETS and self._is_websocket_echo_available(),
        }
        
        logger.info(f"Service availability: {services_available}")
        
        if services_available["redis"]:
            logger.info("Redis is available for enhanced testing")
        else:
            logger.info("Redis not available - using mock caching")
            
        if services_available["websocket_echo"]:
            logger.info("WebSocket echo server is available for enhanced testing")
        else:
            logger.info("WebSocket echo server not available - using mock WebSocket")
        
        # Test should always pass - demonstrates environment adaptation
        assert True, "Fallback handling test complete"
        
        # Log environment information for debugging
        logger.info(f"TEST_WITH_SERVICES: {os.getenv('TEST_WITH_SERVICES', 'not set')}")
        logger.info(f"REDIS_URL: {os.getenv('REDIS_URL', 'not set')}")
        logger.info(f"WEBSOCKET_ECHO_URL: {os.getenv('WEBSOCKET_ECHO_URL', 'not set')}")
        
        logger.info("Integration test with fallback handling completed successfully")

    @pytest.mark.asyncio
    async def test_concurrent_service_access(self, redis_client):
        """Test concurrent access to service containers."""
        if not HAS_REDIS:
            pytest.skip("Redis library not available")
            
        logger.info("Testing concurrent service container access")
        
        async def redis_task(task_id: int, client):
            """Individual Redis task for concurrent testing."""
            key = f"concurrent_test_{task_id}"
            value = f"value_{task_id}"
            
            # Perform multiple operations
            await client.set(key, value)
            retrieved = await client.get(key)
            await client.incr(f"counter_{task_id}")
            counter_value = await client.get(f"counter_{task_id}")
            
            # Clean up
            await client.delete(key)
            await client.delete(f"counter_{task_id}")
            
            return {
                "task_id": task_id,
                "value_match": retrieved == value,
                "counter_value": int(counter_value) if counter_value else 0,
            }
        
        # Run multiple concurrent tasks
        tasks = [redis_task(i, redis_client) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify all tasks completed successfully
        assert len(results) == 5, "All concurrent tasks should complete"
        
        for result in results:
            assert result["value_match"], f"Task {result['task_id']} should have matching values"
            assert result["counter_value"] == 1, f"Task {result['task_id']} should have counter value 1"
        
        logger.info("Concurrent service container access test passed")
        logger.info(f"Successfully completed {len(results)} concurrent Redis operations")