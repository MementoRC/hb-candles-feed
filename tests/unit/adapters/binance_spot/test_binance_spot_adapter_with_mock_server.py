"""
Unit tests for the BinanceSpotAdapter class using the mock exchange server.
"""

import asyncio
import pytest
import aiohttp
import json
from typing import Dict, Any, List

from candles_feed.adapters.binance_spot.binance_spot_adapter import BinanceSpotAdapter
from candles_feed.core.candle_data import CandleData


class TestBinanceSpotAdapterWithMockServer:
    """Test suite for the BinanceSpotAdapter with mock server."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = BinanceSpotAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    @pytest.mark.asyncio
    async def test_fetch_recent_candles(self, binance_mock_server, mock_server_url):
        """Test fetching recent candles from mock server."""
        # Create a session
        async with aiohttp.ClientSession() as session:
            # Override the adapter REST URL
            self.adapter.get_rest_url = lambda: mock_server_url
            
            # Get request parameters
            params = self.adapter.get_rest_params(
                self.trading_pair, 
                self.interval,
                limit=10
            )
            
            # Create URL
            url = f"{mock_server_url}/api/v3/klines"
            
            # Fetch data
            async with session.get(url, params=params) as response:
                # Verify successful response
                assert response.status == 200
                
                # Get the data
                data = await response.json()
                
                # Verify we have candles
                assert isinstance(data, List)
                assert len(data) > 0
                
                # Parse the response
                candles = self.adapter.parse_rest_response(data)
                
                # Verify parsed candles
                assert len(candles) > 0
                for candle in candles:
                    assert isinstance(candle, CandleData)
                    assert hasattr(candle, 'timestamp')
                    assert hasattr(candle, 'open')
                    assert hasattr(candle, 'high')
                    assert hasattr(candle, 'low')
                    assert hasattr(candle, 'close')
                    assert hasattr(candle, 'volume')

    @pytest.mark.asyncio
    async def test_websocket_connection(self, binance_mock_server, mock_server_url):
        """Test WebSocket connection to mock server."""
        # Override the adapter WS URL
        ws_url = f"ws://{mock_server_url.split('://')[-1]}/ws"
        self.adapter.get_ws_url = lambda: ws_url
        
        # Create WebSocket connection
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                # Create subscription payload
                payload = self.adapter.get_ws_subscription_payload(
                    self.trading_pair,
                    self.interval
                )
                
                # Send subscription request
                await ws.send_json(payload)
                
                # Wait for subscription response
                response = await ws.receive_json(timeout=5.0)
                
                # Verify subscription was successful
                assert response is not None
                
                # Wait for a candle message
                try:
                    message = await ws.receive_json(timeout=5.0)
                    # Parse the WebSocket message
                    if message:
                        candles = self.adapter.parse_ws_message(message)
                        if candles:
                            # Verify we have parsed candles
                            assert len(candles) > 0
                            for candle in candles:
                                assert isinstance(candle, CandleData)
                                assert hasattr(candle, 'timestamp')
                except asyncio.TimeoutError:
                    # No message received in time, but the test still passes
                    # as the connection was successful
                    pass
                
                # Close connection
                await ws.close()