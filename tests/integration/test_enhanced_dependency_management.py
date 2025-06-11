"""
Enhanced integration tests with improved external dependency management.

This module demonstrates improved integration testing strategies that enhance
the reliability and scope of existing mock-based tests by:
- Better mock server lifecycle management
- Enhanced network condition simulation
- Improved error handling and recovery testing
- More realistic timing and concurrency scenarios

These improvements work within the existing architecture while providing
more comprehensive coverage of external dependency scenarios.
"""

import asyncio
import logging
import time

import pytest

from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.network_config import NetworkConfig
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
class TestEnhancedDependencyManagement:
    """Enhanced integration tests with improved external dependency management."""

    @pytest.fixture
    async def enhanced_mock_server(self, unused_tcp_port):
        """Create enhanced mock server with better lifecycle management."""
        plugin = BinanceSpotPlugin()
        server = MockedExchangeServer(plugin, "127.0.0.1", unused_tcp_port)

        # Add comprehensive trading pair coverage
        trading_pairs = [
            ("BTCUSDT", ["1m", "5m", "15m", "1h"], 50000.0),
            ("ETHUSDT", ["1m", "5m", "15m"], 3000.0),
            ("ADAUSDT", ["1m", "5m"], 1.5),
            ("SOLUSDT", ["1m"], 100.0),
        ]

        for symbol, intervals, base_price in trading_pairs:
            for interval in intervals:
                server.add_trading_pair(symbol, interval, base_price)

        # Configure enhanced network conditions for testing
        server.set_network_conditions(
            latency_ms=10,  # Realistic latency
            packet_loss_rate=0.0,  # Start with reliable connection
            error_rate=0.0,  # Start with no errors
        )

        # Start server with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = await server.start()
                server.url = url
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Server start attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)

        logger.info(f"Enhanced mock server started at {server.url}")
        yield server

        # Enhanced cleanup with error handling
        try:
            await server.stop()
        except Exception as e:
            logger.warning(f"Error stopping server: {e}")

    def patch_feed_urls(self, feed, mock_server):
        """Enhanced URL patching with better error handling."""
        adapter_class = feed._adapter.__class__

        # Store original methods for restoration
        original_methods = {
            "rest_url": getattr(adapter_class, "_get_rest_url", None),
            "ws_url": getattr(adapter_class, "_get_ws_url", None),
        }

        # Check if adapter has testnet support
        if hasattr(feed._adapter, "_bypass_network_selection"):
            feed._adapter._bypass_network_selection = True
            original_methods["bypass_network_selection"] = True

        # Patch URLs with error handling
        try:
            rest_url = f"{mock_server.url}/api/v3/klines"
            ws_url = f"ws://{mock_server.host}:{mock_server.port}/ws"

            # Patch REST URL
            if hasattr(adapter_class, "_get_rest_url"):
                import inspect

                if isinstance(inspect.getattr_static(adapter_class, "_get_rest_url"), staticmethod):
                    adapter_class._get_rest_url = lambda: rest_url
                else:
                    adapter_class._get_rest_url = lambda self: rest_url

            # Patch WebSocket URL
            if hasattr(adapter_class, "_get_ws_url"):
                import inspect

                if isinstance(inspect.getattr_static(adapter_class, "_get_ws_url"), staticmethod):
                    adapter_class._get_ws_url = lambda: ws_url
                else:
                    adapter_class._get_ws_url = lambda self: ws_url

            logger.info(f"Patched URLs - REST: {rest_url}, WS: {ws_url}")

        except Exception as e:
            logger.error(f"Error patching URLs: {e}")
            raise

        return original_methods

    def restore_feed_urls(self, feed, original_methods):
        """Enhanced URL restoration with error handling."""
        try:
            adapter_class = feed._adapter.__class__

            # Restore original methods
            if original_methods.get("rest_url"):
                adapter_class._get_rest_url = original_methods["rest_url"]
            if original_methods.get("ws_url"):
                adapter_class._get_ws_url = original_methods["ws_url"]

            # Restore bypass flag
            if hasattr(feed._adapter, "_bypass_network_selection"):
                feed._adapter._bypass_network_selection = original_methods.get(
                    "bypass_network_selection", False
                )

            logger.info("Successfully restored original URLs")

        except Exception as e:
            logger.warning(f"Error restoring URLs: {e}")

    @pytest.mark.asyncio
    async def test_enhanced_network_condition_simulation(self, enhanced_mock_server):
        """Test enhanced network condition simulation for external dependencies."""
        logger.info("Testing enhanced network condition simulation")

        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=50,
            network_config=NetworkConfig.for_testing(),
        )

        original_methods = self.patch_feed_urls(feed, enhanced_mock_server)

        try:
            # Test 1: Normal conditions
            enhanced_mock_server.set_network_conditions(
                latency_ms=5, packet_loss_rate=0.0, error_rate=0.0
            )

            start_time = time.time()
            await feed.fetch_candles(limit=10)
            normal_duration = time.time() - start_time

            candles = feed.get_candles()
            assert len(candles) > 0, "Should fetch candles under normal conditions"
            logger.info(f"Normal conditions: {len(candles)} candles in {normal_duration:.3f}s")

            # Test 2: High latency conditions
            enhanced_mock_server.set_network_conditions(
                latency_ms=200, packet_loss_rate=0.0, error_rate=0.0
            )

            feed._candles.clear()  # Clear previous data
            start_time = time.time()
            await feed.fetch_candles(limit=10)
            high_latency_duration = time.time() - start_time

            candles = feed.get_candles()
            assert len(candles) > 0, "Should fetch candles under high latency"
            assert high_latency_duration > normal_duration, "High latency should take longer"
            logger.info(f"High latency: {len(candles)} candles in {high_latency_duration:.3f}s")

            # Test 3: Moderate error conditions with retry
            enhanced_mock_server.set_network_conditions(
                latency_ms=50, packet_loss_rate=0.1, error_rate=0.1
            )

            success_count = 0
            total_attempts = 5

            for attempt in range(total_attempts):
                try:
                    feed._candles.clear()
                    await asyncio.wait_for(feed.fetch_candles(limit=5), timeout=10.0)
                    candles = feed.get_candles()
                    if len(candles) > 0:
                        success_count += 1
                    logger.info(f"Attempt {attempt + 1}: {len(candles)} candles")
                except (asyncio.TimeoutError, Exception) as e:
                    logger.info(f"Expected error on attempt {attempt + 1}: {type(e).__name__}")

                await asyncio.sleep(0.5)  # Brief pause between attempts

            # Should have some successes despite error conditions
            success_rate = success_count / total_attempts
            logger.info(f"Success rate under error conditions: {success_rate:.1%}")
            assert success_rate > 0, "Should have some success even with error conditions"

            # Test 4: Recovery after network issues
            enhanced_mock_server.set_network_conditions(
                latency_ms=10, packet_loss_rate=0.0, error_rate=0.0
            )

            feed._candles.clear()
            await feed.fetch_candles(limit=10)
            recovery_candles = feed.get_candles()

            assert len(recovery_candles) > 0, "Should recover after network issues resolved"
            logger.info(f"Recovery test: {len(recovery_candles)} candles after conditions improved")

        finally:
            self.restore_feed_urls(feed, original_methods)
            if hasattr(feed, "_network_client") and feed._network_client:
                await feed._network_client.close()

    @pytest.mark.asyncio
    async def test_concurrent_external_dependency_access(self, enhanced_mock_server):
        """Test concurrent access to external dependencies with enhanced management."""
        logger.info("Testing concurrent external dependency access")

        # Create multiple feeds for concurrent testing
        feeds = []
        original_methods_list = []

        trading_pairs = ["BTC-USDT", "ETH-USDT", "ADA-USDT"]

        for pair in trading_pairs:
            feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair=pair,
                interval="1m",
                max_records=30,
                network_config=NetworkConfig.for_testing(),
            )
            feeds.append(feed)
            original_methods = self.patch_feed_urls(feed, enhanced_mock_server)
            original_methods_list.append(original_methods)

        try:
            # Test concurrent fetch operations
            async def fetch_for_feed(feed, feed_name):
                """Fetch candles for a specific feed."""
                try:
                    await feed.fetch_candles(limit=5)
                    candles = feed.get_candles()
                    return {
                        "feed": feed_name,
                        "success": True,
                        "candle_count": len(candles),
                        "last_price": candles[-1].close if candles else None,
                    }
                except Exception as e:
                    return {
                        "feed": feed_name,
                        "success": False,
                        "error": str(e),
                        "candle_count": 0,
                    }

            # Run concurrent operations
            tasks = [fetch_for_feed(feed, pair) for feed, pair in zip(feeds, trading_pairs)]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_duration = time.time() - start_time

            # Verify results
            successful_feeds = 0
            total_candles = 0

            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    successful_feeds += 1
                    total_candles += result.get("candle_count", 0)
                    logger.info(
                        f"Feed {result['feed']}: {result['candle_count']} candles, "
                        f"last price: {result.get('last_price', 'N/A')}"
                    )
                else:
                    logger.warning(f"Feed failed: {result}")

            assert successful_feeds > 0, "At least one feed should succeed"
            assert total_candles > 0, "Should receive candles from successful feeds"

            logger.info(
                f"Concurrent test completed: {successful_feeds}/{len(feeds)} feeds successful, "
                f"{total_candles} total candles in {total_duration:.3f}s"
            )

            # Test concurrent stress with network conditions
            enhanced_mock_server.set_network_conditions(
                latency_ms=100, packet_loss_rate=0.05, error_rate=0.05
            )

            stress_tasks = [
                fetch_for_feed(feed, f"{pair}_stress") for feed, pair in zip(feeds, trading_pairs)
            ]

            stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            stress_successes = sum(
                1 for result in stress_results if isinstance(result, dict) and result.get("success")
            )

            logger.info(f"Stress test: {stress_successes}/{len(feeds)} feeds successful under load")

        finally:
            # Restore all feeds and close their network clients
            for feed_item, original_methods_item in zip(feeds, original_methods_list):
                self.restore_feed_urls(feed_item, original_methods_item)
                if hasattr(feed_item, "_network_client") and feed_item._network_client:
                    await feed_item._network_client.close()

    @pytest.mark.asyncio
    async def test_external_dependency_failure_recovery(self, enhanced_mock_server):
        """Test recovery from external dependency failures."""
        logger.info("Testing external dependency failure recovery")

        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=50,
            network_config=NetworkConfig.for_testing(),
        )

        original_methods = self.patch_feed_urls(feed, enhanced_mock_server)

        try:
            # Step 1: Establish baseline with working connection
            await feed.fetch_candles(limit=5)
            baseline_candles = feed.get_candles()
            assert len(baseline_candles) > 0, "Should establish baseline connection"
            logger.info(f"Baseline established: {len(baseline_candles)} candles")

            # Step 2: Simulate severe network issues
            enhanced_mock_server.set_network_conditions(
                latency_ms=500,  # High latency but not excessive
                packet_loss_rate=0.3,  # Moderate packet loss
                error_rate=0.2,  # Moderate error rate
            )

            # Attempt to fetch under severe conditions
            failure_count = 0
            max_failure_attempts = 3

            for attempt in range(max_failure_attempts):
                try:
                    await asyncio.wait_for(feed.fetch_candles(limit=3), timeout=5.0)
                    logger.info(f"Unexpected success on attempt {attempt + 1}")
                except (asyncio.TimeoutError, Exception) as e:
                    failure_count += 1
                    logger.info(f"Expected failure {failure_count}: {type(e).__name__}")

            # Network simulation is probabilistic, so we just log the behavior
            # The important thing is that the test doesn't crash under these conditions
            logger.info(
                f"Network simulation results: {failure_count}/{max_failure_attempts} failures observed"
            )

            # Step 3: Gradually improve conditions and test recovery
            recovery_stages = [
                {"latency_ms": 500, "packet_loss_rate": 0.3, "error_rate": 0.2},
                {"latency_ms": 100, "packet_loss_rate": 0.1, "error_rate": 0.05},
                {"latency_ms": 20, "packet_loss_rate": 0.0, "error_rate": 0.0},
            ]

            for stage_num, conditions in enumerate(recovery_stages, 1):
                enhanced_mock_server.set_network_conditions(**conditions)
                logger.info(f"Recovery stage {stage_num}: {conditions}")

                # Try to recover
                recovery_attempts = 3
                recovery_success = False

                for attempt in range(recovery_attempts):
                    try:
                        feed._candles.clear()
                        await asyncio.wait_for(feed.fetch_candles(limit=5), timeout=10.0)
                        candles = feed.get_candles()

                        if len(candles) > 0:
                            recovery_success = True
                            logger.info(
                                f"Recovery successful at stage {stage_num}, attempt {attempt + 1}: "
                                f"{len(candles)} candles"
                            )
                            break
                    except Exception as e:
                        logger.info(
                            f"Recovery attempt {attempt + 1} failed at stage {stage_num}: "
                            f"{type(e).__name__}"
                        )
                        await asyncio.sleep(1)

                if recovery_success:
                    break

            assert recovery_success, "Should eventually recover as conditions improve"

            # Step 4: Verify full recovery
            final_candles = feed.get_candles()
            assert len(final_candles) >= len(baseline_candles), (
                "Should have at least as many candles as baseline after recovery"
            )

            logger.info("External dependency failure recovery test completed successfully")

        finally:
            # Reset to normal conditions
            enhanced_mock_server.set_network_conditions(
                latency_ms=10, packet_loss_rate=0.0, error_rate=0.0
            )
            self.restore_feed_urls(feed, original_methods)

    @pytest.mark.asyncio
    async def test_realistic_external_api_simulation(self, enhanced_mock_server):
        """Test realistic external API behavior simulation."""
        logger.info("Testing realistic external API behavior simulation")

        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100,
            network_config=NetworkConfig.for_testing(),
        )

        original_methods = self.patch_feed_urls(feed, enhanced_mock_server)

        try:
            # Test realistic API timing patterns
            test_scenarios = [
                {
                    "name": "Peak hours simulation",
                    "conditions": {"latency_ms": 150, "packet_loss_rate": 0.02, "error_rate": 0.01},
                    "expected_success_rate": 0.9,
                },
                {
                    "name": "Normal hours simulation",
                    "conditions": {
                        "latency_ms": 50,
                        "packet_loss_rate": 0.005,
                        "error_rate": 0.001,
                    },
                    "expected_success_rate": 0.98,
                },
                {
                    "name": "Maintenance window simulation",
                    "conditions": {"latency_ms": 300, "packet_loss_rate": 0.1, "error_rate": 0.15},
                    "expected_success_rate": 0.7,
                },
            ]

            for scenario in test_scenarios:
                logger.info(f"Testing scenario: {scenario['name']}")
                enhanced_mock_server.set_network_conditions(**scenario["conditions"])

                # Perform multiple requests to get statistical data
                attempts = 10
                successes = 0
                total_duration = 0

                for _attempt in range(attempts):
                    try:
                        start_time = time.time()
                        feed._candles.clear()
                        await asyncio.wait_for(feed.fetch_candles(limit=5), timeout=15.0)
                        duration = time.time() - start_time

                        candles = feed.get_candles()
                        if len(candles) > 0:
                            successes += 1
                            total_duration += duration

                    except Exception as e:
                        logger.debug(f"Expected failure in {scenario['name']}: {type(e).__name__}")

                    await asyncio.sleep(0.2)  # Realistic API call spacing

                success_rate = successes / attempts
                avg_duration = total_duration / successes if successes > 0 else 0

                logger.info(
                    f"{scenario['name']}: {success_rate:.1%} success rate, "
                    f"avg duration: {avg_duration:.3f}s"
                )

                # Verify the success rate is within expected range (with some tolerance)
                assert success_rate >= (scenario["expected_success_rate"] - 0.2), (
                    f"{scenario['name']} success rate too low: {success_rate:.1%}"
                )

            # Test API rate limiting simulation
            logger.info("Testing API rate limiting behavior")
            enhanced_mock_server.set_network_conditions(
                latency_ms=20,
                packet_loss_rate=0.0,
                error_rate=0.3,  # High error rate for rate limiting
            )

            # Rapid-fire requests to trigger rate limiting
            rapid_requests = 5
            rate_limit_errors = 0

            for i in range(rapid_requests):
                try:
                    feed._candles.clear()
                    await asyncio.wait_for(feed.fetch_candles(limit=3), timeout=5.0)
                    logger.info(f"Rapid request {i + 1} succeeded")
                except Exception as e:
                    rate_limit_errors += 1
                    logger.info(f"Rapid request {i + 1} failed (rate limiting): {type(e).__name__}")

                # No sleep - simulate rapid requests

            logger.info(f"Rate limiting test: {rate_limit_errors}/{rapid_requests} requests failed")

        finally:
            # Reset to normal conditions
            enhanced_mock_server.set_network_conditions(
                latency_ms=10, packet_loss_rate=0.0, error_rate=0.0
            )
            self.restore_feed_urls(feed, original_methods)
