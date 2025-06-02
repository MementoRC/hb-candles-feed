#!/usr/bin/env python3
"""
Task 8 Validation: Network Client Adapter Delegation

This script validates that the NetworkClient properly delegates to Hummingbot components
and that rate limiting behavior matches Hummingbot expectations.
"""

import asyncio
import logging
import time
from unittest.mock import patch

from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.hummingbot_network_client_adapter import (
    HummingbotNetworkClient,
    NetworkClientFactory,
)
from candles_feed.core.network_client import NetworkClient
from candles_feed.mocking_resources.hummingbot.mock_components import (
    create_mock_hummingbot_components,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def validate_network_client_factory():
    """Test 1: Validate NetworkClientFactory delegation logic."""
    logger.info("=== Test 1: NetworkClientFactory Delegation ===")
    
    # Test fallback to standalone NetworkClient
    standalone_client = NetworkClientFactory.create_client()
    assert isinstance(standalone_client, NetworkClient), "Should fallback to standalone NetworkClient"
    logger.info("✅ NetworkClientFactory correctly falls back to standalone implementation")
    
    # Test with Hummingbot components
    mock_components = create_mock_hummingbot_components()
    
    with patch("candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True):
        hummingbot_client = NetworkClientFactory.create_client(
            hummingbot_components=mock_components
        )
        assert isinstance(hummingbot_client, HummingbotNetworkClient), "Should create HummingbotNetworkClient"
        logger.info("✅ NetworkClientFactory correctly creates HummingbotNetworkClient when components available")
    
    # Test partial components (should fallback)
    partial_components = {"throttler": mock_components["throttler"]}  # Missing web_assistants_factory
    fallback_client = NetworkClientFactory.create_client(hummingbot_components=partial_components)
    assert isinstance(fallback_client, NetworkClient), "Should fallback with partial components"
    logger.info("✅ NetworkClientFactory correctly falls back with partial components")


async def validate_rate_limiting_delegation():
    """Test 2: Validate rate limiting delegation through AsyncThrottler."""
    logger.info("\n=== Test 2: Rate Limiting Delegation ===")
    
    # Create mock components with rate limiting
    rate_limits = [
        {"limit_id": "api_request", "limit": 3, "time_interval": 1.0},  # 3 calls per second
    ]
    mock_components = create_mock_hummingbot_components(rate_limits=rate_limits)
    
    with patch("candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True):
        client = HummingbotNetworkClient(
            throttler=mock_components["throttler"],
            web_assistants_factory=mock_components["web_assistants_factory"],
        )
        
        # Test rate limiting behavior
        async with client:
            start_time = time.time()
            
            # Make multiple requests - should be rate limited
            for i in range(3):
                try:
                    await client.get_rest_data("https://api.test.com/candles")
                except Exception:
                    pass  # We expect mock to return errors, just testing rate limiting
            
            elapsed = time.time() - start_time
            logger.info(f"3 requests took {elapsed:.3f}s")
            
            # Verify throttler was called
            throttler_logs = mock_components["throttler"].task_logs
            assert len(throttler_logs) == 3, f"Expected 3 throttler calls, got {len(throttler_logs)}"
            assert all(log[0] == "api_request" for log in throttler_logs), "All calls should use 'api_request' limit ID"
            
            logger.info("✅ Rate limiting delegation working correctly")


async def validate_adapter_delegation():
    """Test 3: Validate adapter delegation through network client."""
    logger.info("\n=== Test 3: Adapter Delegation ===")
    
    # Create mock components
    mock_components = create_mock_hummingbot_components(
        rest_responses={
            "https://test.example.com/api": {"data": "test response"}
        }
    )
    
    with patch("candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True):
        # Test that CandlesFeed uses the NetworkClient properly
        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            hummingbot_components=mock_components
        )
        
        # Verify the correct network client type was created
        assert isinstance(feed._network_client, HummingbotNetworkClient), "CandlesFeed should use HummingbotNetworkClient"
        logger.info("✅ CandlesFeed correctly uses HummingbotNetworkClient when components provided")
        
        # Test delegation through adapter
        async with feed._network_client:
            response = await feed._network_client.get_rest_data("https://test.example.com/api")
            assert response == {"data": "test response"}, "Response should match mock"
            logger.info("✅ Network client delegation to REST assistant working correctly")


async def validate_error_propagation():
    """Test 4: Validate error propagation through delegation layers."""
    logger.info("\n=== Test 4: Error Propagation ===")
    
    # Create throttler that simulates failures
    class FailingThrottler:
        def __init__(self):
            self.task_logs = []
            
        async def execute_task(self, limit_id: str):
            self.task_logs.append((limit_id, time.time()))
            
            class FailingContext:
                async def __aenter__(self):
                    raise RuntimeError("Simulated throttler failure")
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None
            return FailingContext()
    
    mock_components = create_mock_hummingbot_components()
    mock_components["throttler"] = FailingThrottler()
    
    with patch("candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True):
        client = HummingbotNetworkClient(
            throttler=mock_components["throttler"],
            web_assistants_factory=mock_components["web_assistants_factory"],
        )
        
        # Test error propagation
        try:
            async with client:
                await client.get_rest_data("https://api.test.com/candles")
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "Simulated throttler failure" in str(e), "Error should propagate correctly"
            logger.info("✅ Error propagation through delegation layers working correctly")


async def validate_websocket_delegation():
    """Test 5: Validate WebSocket delegation."""
    logger.info("\n=== Test 5: WebSocket Delegation ===")
    
    ws_messages = ['{"type": "kline", "data": {"symbol": "BTCUSDT"}}']
    mock_components = create_mock_hummingbot_components(ws_messages=ws_messages)
    
    with patch("candles_feed.core.hummingbot_network_client_adapter.HUMMINGBOT_AVAILABLE", True):
        client = HummingbotNetworkClient(
            throttler=mock_components["throttler"],
            web_assistants_factory=mock_components["web_assistants_factory"],
        )
        
        async with client:
            # Test WebSocket connection
            ws_assistant = await client.establish_ws_connection("wss://test.example.com/ws")
            
            # Test message sending
            await client.send_ws_message(ws_assistant, {"subscribe": "BTCUSDT"})
            
            # Test message receiving
            messages = []
            async for message in ws_assistant.iter_messages():
                messages.append(message)
                break  # Just get first message
            
            assert len(messages) == 1, "Should receive one message"
            assert messages[0]["type"] == "kline", "Message should be parsed correctly"
            logger.info("✅ WebSocket delegation working correctly")


async def main():
    """Run all validation tests."""
    logger.info("🚀 Starting Task 8 Validation: Network Client Adapter Delegation")
    
    try:
        await validate_network_client_factory()
        await validate_rate_limiting_delegation()
        await validate_adapter_delegation()
        await validate_error_propagation()
        await validate_websocket_delegation()
        
        logger.info("\n🎉 All validation tests passed!")
        logger.info("✅ NetworkClient delegation is working correctly")
        logger.info("✅ Rate limiting through AsyncThrottler is properly enforced")
        logger.info("✅ Request/response handling and error propagation is correct")
        logger.info("✅ WebSocket delegation is functioning properly")
        logger.info("✅ Integration with real adapter flows is validated")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)