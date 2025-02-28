"""
Protocol definitions for the Candle Feed framework.

This module defines the core interface contracts for the framework
using Python's typing.Protocol system.
"""

from typing import Any, AsyncGenerator, Dict, List, Optional, Protocol, runtime_checkable

from candles_feed.core.candle_data import CandleData


@runtime_checkable
class CandleDataAdapter(Protocol):
    """Protocol for exchange adapters.
    
    This protocol defines the interface that all exchange adapters must implement.
    """
    
    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.
        
        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
            
        Returns:
            Trading pair in exchange-specific format
        """
        ...
    
    def get_rest_url(self) -> str:
        """Get REST API URL for candles.
        
        Returns:
            REST API URL
        """
        ...
    
    def get_ws_url(self) -> str:
        """Get WebSocket URL.
        
        Returns:
            WebSocket URL
        """
        ...
    
    def get_rest_params(self, trading_pair: str, interval: str, 
                      start_time: Optional[int] = None, 
                      end_time: Optional[int] = None, 
                      limit: Optional[int] = None) -> dict:
        """Get parameters for REST API request.
        
        Args:
            trading_pair: Trading pair
            interval: Candle interval
            start_time: Start time in seconds
            end_time: End time in seconds
            limit: Maximum number of candles to return
            
        Returns:
            Dictionary of parameters for REST API request
        """
        ...
    
    def parse_rest_response(self, data: Any) -> List[CandleData]:
        """Parse REST API response into CandleData objects.
        
        Args:
            data: REST API response
            
        Returns:
            List of CandleData objects
        """
        ...
    
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.
        
        Args:
            trading_pair: Trading pair
            interval: Candle interval
            
        Returns:
            WebSocket subscription payload
        """
        ...
    
    def parse_ws_message(self, data: Any) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.
        
        Args:
            data: WebSocket message
            
        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        ...
    
    def get_supported_intervals(self) -> Dict[str, int]:
        """Get supported intervals and their durations in seconds.
        
        Returns:
            Dictionary mapping interval strings to their duration in seconds
        """
        ...
    
    def get_ws_supported_intervals(self) -> List[str]:
        """Get intervals supported by WebSocket API.
        
        Returns:
            List of interval strings supported by WebSocket API
        """
        ...


@runtime_checkable
class WSAssistant(Protocol):
    """Protocol for WebSocket assistants."""
    
    async def connect(self) -> None:
        """Connect to WebSocket."""
        ...
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        ...
    
    async def send(self, payload: Any) -> None:
        """Send request to WebSocket.
        
        Args:
            payload: Message payload to send
        """
        ...
    
    def iter_messages(self) -> AsyncGenerator[Any, None]:
        """Iterate over WebSocket messages.
        
        Returns:
            AsyncGenerator yielding WebSocket messages
        """
        ...


@runtime_checkable
class NetworkStrategy(Protocol):
    """Protocol for network connection strategies."""
    
    async def poll_once(self, 
                     start_time: Optional[int] = None, 
                     end_time: Optional[int] = None, 
                     limit: Optional[int] = None) -> List[CandleData]:
        """Fetch candles for a specific time range.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            limit: Maximum number of candles to return
            
        Returns:
            List of CandleData objects
        """
        ...
    
    async def start(self) -> None:
        """Start the network strategy."""
        ...
    
    async def stop(self) -> None:
        """Stop the network strategy."""
        ...


class Logger(Protocol):
    """Protocol for loggers."""
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log debug message."""
        ...
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """Log info message."""
        ...
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log warning message."""
        ...
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """Log error message."""
        ...
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        """Log exception message."""
        ...