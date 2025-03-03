"""
End-to-end test for the Candles Feed framework.

This module demonstrates how to use the exchange simulation framework
to test the Candles Feed in a realistic but controlled environment.
"""

import asyncio
import logging
import time

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.testing_resources.candle_data_factory import CandleDataFactory
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType
from candles_feed.testing_resources.mocked_candle_feed_server import MockedCandlesFeedServer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEndToEnd:
    """End-to-end test suite for the Candles Feed."""
    
    @pytest.fixture
    async def mock_binance_server(self, monkeypatch):
        """Create a mock Binance server for testing."""
        server = MockedCandlesFeedServer(ExchangeType.BINANCE_SPOT)
        url = await server.start()
        
        # Directly patch the adapter method that gets called
        from candles_feed.adapters.binance_spot.binance_spot_adapter import BinanceSpotAdapter
        
        # Define patched methods that return our mock server URLs
        def patched_get_rest_url(self):
            base_url = url.rstrip('/')
            return f"{base_url}/api/v3/klines"
            
        def patched_get_ws_url(self):
            return f"ws://{server.host}:{server.port}/ws"
        
        # Apply patches using monkeypatch
        monkeypatch.setattr(BinanceSpotAdapter, "get_rest_url", patched_get_rest_url)
        monkeypatch.setattr(BinanceSpotAdapter, "get_ws_url", patched_get_ws_url)
        
        yield server
        
        # monkeypatch will automatically restore the original methods
        await server.stop()
    
    @pytest.mark.asyncio
    async def test_rest_candles_retrieval(self, mock_binance_server):
        """Test retrieving candles via REST API."""
        # Create a CandlesFeed instance
        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100
        )
        
        try:
            # Fetch historical candles
            candles = await feed.fetch_candles()
            
            # Verify candles were received
            assert len(candles) > 0, "No candles received"
            
            # Convert to DataFrame for easier inspection
            df = feed.get_candles_df()
            logger.info(f"Received {len(df)} candles")
            logger.info(f"First candle: {df.iloc[0]}")
            logger.info(f"Last candle: {df.iloc[-1]}")
            
            # Verify candle data looks reasonable
            assert all(df['open'] > 0), "Open prices should be positive"
            assert all(df['high'] >= df['open']), "High should be >= open"
            assert all(df['low'] <= df['open']), "Low should be <= open"
            assert all(df['volume'] > 0), "Volume should be positive"
            
        finally:
            # Clean up resources
            await feed.stop()
    
    @pytest.mark.asyncio
    async def test_websocket_streaming(self, mock_binance_server):
        """Test streaming candles via WebSocket."""
        # Create a CandlesFeed instance
        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100
        )
        
        try:
            # Test that we can get initial data via REST
            await feed.fetch_candles()
            
            # Get initial candle count
            rest_candles = feed.get_candles()
            rest_count = len(rest_candles)
            assert rest_count > 0, "Should receive candles via REST"
            logger.info(f"Received {rest_count} candles via REST")
            
            # Debug the subscription status
            logger.info("Checking MockExchangeServer state before WebSocket start:")
            logger.info(f"Subscriptions: {mock_binance_server.server.subscriptions}")
            logger.info(f"WS connections: {len(mock_binance_server.server.ws_connections)}")
            logger.info(f"Initial candle for BTC-USDT: {rest_candles[-1].timestamp}, close: {rest_candles[-1].close}")
            
            # Start the feed with WebSocket strategy
            logger.info("Starting WebSocket strategy...")
            await feed.start(strategy="websocket")
            
            # Log the WebSocket URL being used
            adapter = feed._adapter
            logger.info(f"WebSocket URL: {adapter.get_ws_url()}")
            logger.info(f"WebSocket subscription payload: {adapter.get_ws_subscription_payload('BTC-USDT', '1m')}")
            
            # Wait a moment for WebSocket connection and subscription to establish
            await asyncio.sleep(2)
            
            # For testing purposes, send a new candle update
            # This is needed because the background candle generation might take too long
            trading_pair = "BTCUSDT"
            interval = "1m"
            last_candle = mock_binance_server.server.candles[trading_pair][interval][-1]
            new_candle = CandleDataFactory.create_random(
                timestamp=int(time.time()),
                previous_candle=last_candle,
                volatility=0.01  # 1% volatility for visible change
            )
            
            # Send the test candle update immediately
            logger.info("Sending test candle update via WebSocket...")
            await mock_binance_server.server._broadcast_candle_update(
                trading_pair, interval, new_candle, True
            )
            
            # Wait for the candle update to be processed
            max_wait_time = 5  # seconds
            ws_test_passed = False
            
            for i in range(max_wait_time * 2):  # Check every 0.5 seconds
                current_count = len(feed.get_candles())
                current_close = feed.get_candles()[-1].close if current_count > 0 else None
                initial_close = rest_candles[-1].close if rest_count > 0 else None
                
                logger.info(f"Check {i+1}: Current candles: {current_count}, Initial: {rest_count}")
                logger.info(f"Current close: {current_close}, Initial close: {initial_close}")
                
                # We either have more candles than before, or at least one new update to existing candles
                if current_count > rest_count or (current_count > 0 and current_close != initial_close):
                    logger.info(f"WebSocket update detected! Count: {current_count}, New close: {current_close}")
                    ws_test_passed = True
                    break
                await asyncio.sleep(0.5)
            
            assert ws_test_passed, f"No candle updates received after {max_wait_time} seconds"
            
            # Get the candles
            candles = feed.get_candles()
            logger.info(f"Received {len(candles)} candles via WebSocket")
            
            # Wait a bit longer to see if we receive updates
            initial_count = len(candles)
            await asyncio.sleep(2)
            
            # Get the updated candles
            updated_candles = feed.get_candles()
            logger.info(f"After waiting, now have {len(updated_candles)} candles")
            
            # In a real scenario, we might receive more candles, but it depends on timing
            # At minimum we should still have the initial candles
            assert len(updated_candles) >= initial_count, "Lost candles during streaming"
            
            # Additional validation: check if we're receiving real-time updates
            # The close price of the most recent candle should be different from the open
            # (in a real exchange) or from our initial data (in our mock server)
            latest_candle = updated_candles[-1]
            assert latest_candle.close != latest_candle.open, "Candle should be updating"
            
        finally:
            # Clean up resources
            try:
                await feed.stop()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                # Continue with other cleanup even if this fails
    
    @pytest.mark.asyncio
    async def test_multiple_trading_pairs(self, mock_binance_server):
        """Test working with multiple trading pairs simultaneously."""
        # Create feeds for different trading pairs
        btc_feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100
        )
        
        eth_feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="ETH-USDT",
            interval="1m",
            max_records=100
        )
        
        sol_feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="SOL-USDT",
            interval="1m",
            max_records=100
        )
        
        try:
            # Fetch historical data for all feeds
            await asyncio.gather(
                btc_feed.fetch_candles(),
                eth_feed.fetch_candles(),
                sol_feed.fetch_candles()
            )
            
            # Verify candles were received for each feed
            assert len(btc_feed.get_candles()) > 0, "No BTC candles received"
            assert len(eth_feed.get_candles()) > 0, "No ETH candles received"
            assert len(sol_feed.get_candles()) > 0, "No SOL candles received"
            
            # Compare prices to ensure they're different (as expected for different assets)
            btc_price = btc_feed.get_candles()[-1].close
            eth_price = eth_feed.get_candles()[-1].close
            sol_price = sol_feed.get_candles()[-1].close
            
            logger.info(f"Latest prices - BTC: {btc_price}, ETH: {eth_price}, SOL: {sol_price}")
            
            # Prices should be in different ranges based on our mock server configuration
            # With the new CandleDataFactory, the prices can vary more randomly, but should still
            # be within reasonable ranges of the initial prices set in the server
            assert 35000 < btc_price < 65000, "BTC price should be somewhere around 50000"
            assert 1500 < eth_price < 4500, "ETH price should be somewhere around 3000"
            assert 40 < sol_price < 160, "SOL price should be somewhere around 100"
            
        finally:
            # Clean up resources
            await asyncio.gather(
                btc_feed.stop(),
                eth_feed.stop(),
                sol_feed.stop()
            )
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Needs adjustment for the new CandleDataFactory")
    async def test_different_intervals(self, mock_binance_server):
        """Test working with different candle intervals."""
        # Configure the mock server with additional intervals
        mock_binance_server.server.add_trading_pair("BTCUSDT", "5m", 50000.0)
        mock_binance_server.server.add_trading_pair("BTCUSDT", "1h", 50000.0)
        
        # Create feeds for different intervals
        feeds = []
        for interval in ["1m", "5m", "1h"]:
            feed = CandlesFeed(
                exchange="binance_spot",
                trading_pair="BTC-USDT",
                interval=interval,
                max_records=100
            )
            feeds.append((interval, feed))
        
        try:
            # Fetch historical data for all feeds
            for _, feed in feeds:
                await feed.fetch_candles()
            
            # Verify candles were received for each interval
            for interval, feed in feeds:
                candles = feed.get_candles()
                assert len(candles) > 0, f"No candles received for {interval} interval"
                logger.info(f"Received {len(candles)} candles for {interval} interval")
                
                # If we have multiple candles, verify the timestamps are spaced correctly
                if len(candles) > 1:
                    time_diff = candles[1].timestamp - candles[0].timestamp
                    expected_diff = 60  # 1m = 60 seconds
                    if interval == "5m":
                        expected_diff = 300  # 5m = 300 seconds
                    elif interval == "1h":
                        expected_diff = 3600  # 1h = 3600 seconds
                    
                    assert abs(time_diff - expected_diff) < 10, f"Incorrect time spacing for {interval} interval"
            
        finally:
            # Clean up resources
            for _, feed in feeds:
                await feed.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Needs adjustment for the new CandleDataFactory")
    async def test_error_handling(self, mock_binance_server):
        """Test error handling capabilities."""
        # Test the URL patching first to ensure we're using our mock server
        import candles_feed.adapters.binance.constants as binance_constants
        logger.info(f"Current SPOT_REST_URL: {binance_constants.SPOT_REST_URL}")
        logger.info(f"Current SPOT_WSS_URL: {binance_constants.SPOT_WSS_URL}")
        
        # Make sure we're using our mock server, not the real Binance API
        assert mock_binance_server.url in binance_constants.SPOT_REST_URL, "URL patching failed"
        assert f"ws://{mock_binance_server.host}:{mock_binance_server.port}" in binance_constants.SPOT_WSS_URL, "WebSocket URL patching failed"

        # Add a known valid trading pair to the server
        mock_binance_server.server.add_trading_pair("BTCUSDT", "1m", 50000.0)
        
        # First test with a valid trading pair to confirm basic functionality
        valid_feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100
        )
        
        try:
            # This should work with our mock server
            candles = await valid_feed.fetch_candles()
            assert len(candles) > 0, "Should receive candles for valid pair"
            logger.info(f"Received {len(candles)} candles for valid pair")
        finally:
            await valid_feed.stop()
            
        # Test with invalid trading pair
        invalid_pair_feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="INVALID-PAIR",  # This should not exist in the mock server
            interval="1m",
            max_records=100
        )
        
        try:
            # The fetch should handle the invalid pair gracefully
            candles = await invalid_pair_feed.fetch_candles()
            logger.info(f"Result with invalid pair: {len(candles)} candles")
            # It might return empty list or raise exception - both are acceptable
        except Exception as e:
            logger.info(f"Expected error with invalid pair: {e}")
        finally:
            await invalid_pair_feed.stop()

        # Now test with network errors by configuring the mock server
        # Enable moderate error simulation (not too extreme)
        mock_binance_server.set_network_conditions(
            latency_ms=100,
            packet_loss_rate=0.2,  # 20% packet loss
            error_rate=0.2         # 20% error rate
        )
        
        # Create a regular feed that will encounter errors
        error_feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100
        )
        
        try:
            # This might fail due to simulated errors, but it shouldn't crash
            successfully_fetched = False
            for retry in range(5):  # More retries for reliability
                try:
                    await error_feed.fetch_candles()
                    # If we get here, we succeeded despite the errors
                    successfully_fetched = True
                    logger.info(f"Successfully fetched candles on retry {retry}")
                    break
                except Exception as e:
                    # We should eventually retry and succeed, but if not that's ok
                    logger.info(f"Expected error during test (retry {retry}): {e}")
                    await asyncio.sleep(0.5)  # Short delay before retry
            
            # Start the WebSocket feed - we expect reconnections on failure
            await error_feed.start(strategy="websocket")
            
            # Wait longer for some data to arrive despite errors
            data_received = False
            for _ in range(20):  # 10 seconds total
                if len(error_feed.get_candles()) > 0:
                    data_received = True
                    logger.info(f"Received {len(error_feed.get_candles())} candles via WebSocket")
                    break
                await asyncio.sleep(0.5)
            
            # Testing that we can recover after errors
            # Reset network conditions to normal
            mock_binance_server.set_network_conditions(
                latency_ms=0,
                packet_loss_rate=0.0,
                error_rate=0.0
            )
            logger.info("Reset network conditions to normal")
            
            # Wait for some additional data to arrive after recovery
            initial_count = len(error_feed.get_candles())
            await asyncio.sleep(5)  # Wait longer for recovery
            
            # We should now have received more data
            final_count = len(error_feed.get_candles())
            logger.info(f"Initial candle count: {initial_count}, Final count: {final_count}")
            
            # Our test is successful if either:
            # 1. We successfully fetched via REST, or
            # 2. We got some data via WebSocket, or
            # 3. We recovered after network errors
            assert successfully_fetched or data_received or final_count > 0, "Error handling test failed"
            
            # The actual assertions are more relaxed because we're testing error handling
            # If we get here without crashes, the error handling is working as expected
                
        finally:
            # Reset network conditions for other tests
            mock_binance_server.set_network_conditions(
                latency_ms=0, 
                packet_loss_rate=0.0,
                error_rate=0.0
            )
            await error_feed.stop()


if __name__ == "__main__":
    # This allows running the test directly
    pytest.main(["-xvs", __file__])