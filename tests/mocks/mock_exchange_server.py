"""
Mock Exchange Server for testing the Candle Feed framework.

This module provides a mock server that simulates exchange APIs (both REST and WebSocket)
for integration testing without connecting to real exchanges.
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union

import aiohttp
from aiohttp import web

from candles_feed.core.candle_data import CandleData


class MockExchangeServer:
    """
    Mock server that simulates a cryptocurrency exchange API.
    
    This class provides both REST and WebSocket endpoints for testing
    exchange adapters without connecting to real exchanges.
    """
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8080):
        """
        Initialize the mock exchange server.
        
        Args:
            host: Host to bind the server to
            port: Port to bind the server to
        """
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.logger = logging.getLogger(__name__)
        
        # WebSocket connections
        self.ws_connections: Set[web.WebSocketResponse] = set()
        self.subscriptions: Dict[str, Set[web.WebSocketResponse]] = {}
        
        # Candle data storage
        self.candles: Dict[str, Dict[str, List[CandleData]]] = {}
        self.last_candle_time: Dict[str, Dict[str, int]] = {}
        
        # Setup routes
        self.setup_routes()
        
        # Candle generation task
        self._candle_generation_task = None
        
    def setup_routes(self):
        """Set up the server routes."""
        # REST endpoints
        self.app.router.add_get('/ping', self.handle_ping)
        self.app.router.add_get('/klines', self.handle_klines)
        self.app.router.add_get('/time', self.handle_time)
        
        # WebSocket endpoint
        self.app.router.add_get('/ws', self.handle_websocket)
    
    async def start(self):
        """Start the mock exchange server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        self.logger.info(f"Mock exchange server started at http://{self.host}:{self.port}")
        
        # Start candle generation task
        self._candle_generation_task = asyncio.create_task(self._generate_candles())
        
        return f"http://{self.host}:{self.port}"
    
    async def stop(self):
        """Stop the mock exchange server."""
        # Stop candle generation task
        if self._candle_generation_task:
            self._candle_generation_task.cancel()
            try:
                await self._candle_generation_task
            except asyncio.CancelledError:
                pass
            self._candle_generation_task = None
        
        # Close all WebSocket connections
        for ws in self.ws_connections:
            await ws.close()
        self.ws_connections.clear()
        self.subscriptions.clear()
        
        # Stop the server
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        self.logger.info("Mock exchange server stopped")
    
    def add_trading_pair(self, trading_pair: str, interval: str, initial_price: float = 50000.0):
        """
        Add a trading pair with initial candle data.
        
        Args:
            trading_pair: Trading pair symbol (e.g., "BTCUSDT")
            interval: Candle interval (e.g., "1m")
            initial_price: Initial price for candle generation
        """
        # Initialize candle storage for the trading pair if needed
        if trading_pair not in self.candles:
            self.candles[trading_pair] = {}
            self.last_candle_time[trading_pair] = {}
        
        # Initialize candle storage for the interval if needed
        if interval not in self.candles[trading_pair]:
            self.candles[trading_pair][interval] = []
            
            # Generate initial candles
            end_time = int(time.time())
            interval_seconds = self._interval_to_seconds(interval)
            
            # Generate 100 historical candles
            for i in range(100):
                timestamp = end_time - (99 - i) * interval_seconds
                
                # Add some price movement
                price_change = (i - 50) / 50.0 * 1000.0  # -1000 to +1000
                current_price = initial_price + price_change
                
                # Create candle with some volatility
                volatility = current_price * 0.01  # 1% volatility
                candle = CandleData(
                    timestamp_raw=timestamp,
                    open=current_price,
                    high=current_price + volatility,
                    low=current_price - volatility,
                    close=current_price + (volatility * 0.2),  # Slight upward bias
                    volume=10.0 + (i % 10),  # Some volume variation
                    quote_asset_volume=(10.0 + (i % 10)) * current_price,
                    n_trades=100 + (i % 100),
                    taker_buy_base_volume=5.0 + (i % 5),
                    taker_buy_quote_volume=(5.0 + (i % 5)) * current_price
                )
                
                self.candles[trading_pair][interval].append(candle)
            
            # Set last candle time
            self.last_candle_time[trading_pair][interval] = end_time
    
    async def _generate_candles(self):
        """Generate new candles periodically for all trading pairs."""
        try:
            while True:
                current_time = int(time.time())
                
                for trading_pair in self.candles:
                    for interval in self.candles[trading_pair]:
                        interval_seconds = self._interval_to_seconds(interval)
                        last_time = self.last_candle_time[trading_pair][interval]
                        
                        # Check if it's time to generate a new candle
                        if current_time >= last_time + interval_seconds:
                            # Get the last candle
                            if self.candles[trading_pair][interval]:
                                last_candle = self.candles[trading_pair][interval][-1]
                                
                                # Generate a new candle with some randomness
                                price_change = (random.random() - 0.5) * 100.0  # -50 to +50
                                new_price = last_candle.close + price_change
                                volatility = new_price * 0.005  # 0.5% volatility
                                
                                new_candle = CandleData(
                                    timestamp_raw=last_time + interval_seconds,
                                    open=last_candle.close,
                                    high=max(new_price, last_candle.close) + volatility,
                                    low=min(new_price, last_candle.close) - volatility,
                                    close=new_price,
                                    volume=10.0 + (random.random() * 10),
                                    quote_asset_volume=(10.0 + (random.random() * 10)) * new_price,
                                    n_trades=100 + int(random.random() * 100),
                                    taker_buy_base_volume=5.0 + (random.random() * 5),
                                    taker_buy_quote_volume=(5.0 + (random.random() * 5)) * new_price
                                )
                                
                                self.candles[trading_pair][interval].append(new_candle)
                                self.last_candle_time[trading_pair][interval] += interval_seconds
                                
                                # Send WebSocket update if there are subscribers
                                channel = f"{trading_pair}@kline_{interval}"
                                await self._broadcast_candle_update(channel, trading_pair, interval, new_candle)
                
                # Wait for a second
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            self.logger.info("Candle generation task cancelled")
            raise
    
    async def _broadcast_candle_update(self, channel: str, trading_pair: str, interval: str, candle: CandleData):
        """Broadcast a candle update to WebSocket subscribers."""
        if channel in self.subscriptions:
            # Format the message based on "Binance-like" format
            message = {
                "e": "kline",
                "E": int(time.time() * 1000),
                "s": trading_pair,
                "k": {
                    "t": candle.timestamp * 1000,
                    "T": (candle.timestamp + self._interval_to_seconds(interval)) * 1000,
                    "s": trading_pair,
                    "i": interval,
                    "f": 1000000,
                    "L": 1000001,
                    "o": str(candle.open),
                    "c": str(candle.close),
                    "h": str(candle.high),
                    "l": str(candle.low),
                    "v": str(candle.volume),
                    "n": candle.n_trades,
                    "x": False,  # Candle not closed
                    "q": str(candle.quote_asset_volume),
                    "V": str(candle.taker_buy_base_volume),
                    "Q": str(candle.taker_buy_quote_volume)
                }
            }
            
            # Send to all subscribers
            for ws in self.subscriptions[channel]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    self.logger.error(f"Error sending WebSocket message: {e}")
    
    def _interval_to_seconds(self, interval: str) -> int:
        """Convert interval string to seconds."""
        unit = interval[-1]
        value = int(interval[:-1])
        
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 60 * 60
        elif unit == 'd':
            return value * 24 * 60 * 60
        elif unit == 'w':
            return value * 7 * 24 * 60 * 60
        elif unit == 'M':
            return value * 30 * 24 * 60 * 60
        else:
            raise ValueError(f"Unknown interval unit: {unit}")

    # REST endpoint handlers
    
    async def handle_ping(self, request):
        """Handle ping endpoint."""
        return web.json_response({})
    
    async def handle_time(self, request):
        """Handle time endpoint."""
        return web.json_response({
            "serverTime": int(time.time() * 1000)
        })
    
    async def handle_klines(self, request):
        """Handle klines (candles) endpoint."""
        # Get query parameters
        params = request.query
        
        symbol = params.get('symbol')
        interval = params.get('interval')
        start_time = params.get('startTime')
        end_time = params.get('endTime')
        limit = params.get('limit', '500')
        
        # Validate parameters
        if not symbol or not interval:
            return web.json_response({"error": "Missing required parameters"}, status=400)
        
        # Check if we have data for this trading pair and interval
        if symbol not in self.candles or interval not in self.candles[symbol]:
            return web.json_response({"error": "No data available"}, status=404)
        
        # Parse time parameters
        start_time_sec = int(start_time) / 1000 if start_time else 0
        end_time_sec = int(end_time) / 1000 if end_time else int(time.time())
        limit_int = min(int(limit), 1000)  # Max 1000 candles
        
        # Filter candles by time range
        filtered_candles = [
            candle for candle in self.candles[symbol][interval]
            if start_time_sec <= candle.timestamp <= end_time_sec
        ]
        
        # Apply limit
        limited_candles = filtered_candles[-limit_int:]
        
        # Convert to Binance format
        response = [
            [
                candle.timestamp * 1000,  # Start time in ms
                str(candle.open),
                str(candle.high),
                str(candle.low),
                str(candle.close),
                str(candle.volume),
                (candle.timestamp + self._interval_to_seconds(interval)) * 1000,  # End time in ms
                str(candle.quote_asset_volume),
                candle.n_trades,
                str(candle.taker_buy_base_volume),
                str(candle.taker_buy_quote_volume),
                "0"  # Ignore
            ]
            for candle in limited_candles
        ]
        
        return web.json_response(response)
    
    # WebSocket endpoint handler
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.ws_connections.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_ws_message(ws, msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f'WebSocket connection closed with exception {ws.exception()}')
        finally:
            # Cleanup on disconnect
            self._remove_ws_connection(ws)
            
        return ws
    
    async def _handle_ws_message(self, ws: web.WebSocketResponse, message: str):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            
            # Handle subscription message (Binance-like format)
            if data.get('method') == 'SUBSCRIBE':
                params = data.get('params', [])
                
                for channel in params:
                    # Parse channel (format: symbol@kline_interval)
                    parts = channel.split('@')
                    if len(parts) != 2 or not parts[1].startswith('kline_'):
                        continue
                    
                    symbol = parts[0].upper()
                    interval = parts[1][6:]  # Remove 'kline_' prefix
                    
                    # Check if we have data for this trading pair and interval
                    if symbol not in self.candles or interval not in self.candles[symbol]:
                        # Add trading pair if it doesn't exist
                        self.add_trading_pair(symbol, interval)
                    
                    # Add subscription
                    if channel not in self.subscriptions:
                        self.subscriptions[channel] = set()
                    self.subscriptions[channel].add(ws)
                
                # Send subscription success response
                await ws.send_json({
                    "result": None,
                    "id": data.get('id', 1)
                })
            
            # Handle unsubscribe message
            elif data.get('method') == 'UNSUBSCRIBE':
                params = data.get('params', [])
                
                for channel in params:
                    if channel in self.subscriptions and ws in self.subscriptions[channel]:
                        self.subscriptions[channel].remove(ws)
                
                # Send unsubscribe success response
                await ws.send_json({
                    "result": None,
                    "id": data.get('id', 1)
                })
                
            # Handle ping message
            elif data.get('method') == 'ping':
                await ws.send_json({
                    "method": "pong",
                    "id": data.get('id', 1)
                })
        
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON message: {message}")
        except Exception as e:
            self.logger.error(f"Error handling WebSocket message: {e}")
    
    def _remove_ws_connection(self, ws: web.WebSocketResponse):
        """Remove WebSocket connection and subscriptions."""
        if ws in self.ws_connections:
            self.ws_connections.remove(ws)
        
        # Remove from subscriptions
        for channel, subscribers in list(self.subscriptions.items()):
            if ws in subscribers:
                subscribers.remove(ws)
                if not subscribers:
                    del self.subscriptions[channel]