"""
Hybrid mock adapter implementing both sync and async patterns for testing.
"""

from typing import Any, Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    SPOT_REST_URL,
    REST_CANDLES_ENDPOINT,
    SPOT_WSS_URL,
    INTERVALS,
    DEFAULT_CANDLES_LIMIT,
)


@ExchangeRegistry.register("hybrid_mocked_adapter")
class HybridMockedAdapter(BaseAdapter):
    """
    Hybrid adapter that implements both sync and async patterns.
    
    This adapter is designed for testing both patterns with
    the candles feed framework.
    """
    
    TIMESTAMP_UNIT = "milliseconds"
    
    def __init__(self, network_client: NetworkClientProtocol = None):
        """Initialize with optional network client.
        
        :param network_client: Optional network client to use
        """
        self._network_client = network_client

    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert trading pair to exchange format.
        
        :param trading_pair: Trading pair in standard format (e.g., BTC-USDT).
        :returns: Trading pair in exchange format (unchanged for simple mock).
        """
        # The mock exchange uses the same format (BTC-USDT)
        return trading_pair
    
    def get_supported_intervals(self) -> Dict[str, int]:
        """Get supported intervals and their duration in seconds.
        
        :returns: Dictionary mapping interval names to seconds.
        """
        return INTERVALS
    
    def get_ws_supported_intervals(self) -> List[str]:
        """Get intervals supported by WebSocket API.
        
        :returns: List of supported interval strings.
        """
        return list(INTERVALS.keys())
    
    def get_ws_url(self) -> str:
        """Get the WebSocket API URL.
        
        :returns: WebSocket API URL.
        """
        return SPOT_WSS_URL
    
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> Dict[str, Any]:
        """Get WebSocket subscription payload.
        
        :param trading_pair: Trading pair in standard format.
        :param interval: Interval string.
        :returns: Subscription payload.
        """
        return {
            "type": "subscribe",
            "subscriptions": [
                {
                    "symbol": self.get_trading_pair_format(trading_pair),
                    "interval": interval
                }
            ]
        }
    
    def parse_ws_message(self, message: dict[str, Any]) -> list[CandleData] | None:
        """Process WebSocket message into CandleData objects.
        
        :param message: WebSocket message.
        :returns: List of CandleData objects or None if the message doesn't contain candle data.
        """
        data = message.get("data", {})
        
        if not data or not data.get("timestamp"):
            return None
            
        timestamp = data.get("timestamp")
        # Convert timestamp to seconds
        timestamp = self.ensure_timestamp_in_seconds(timestamp)
            
        return [CandleData(
            timestamp_raw=timestamp,
            open=float(data.get("open", 0)),
            high=float(data.get("high", 0)),
            low=float(data.get("low", 0)),
            close=float(data.get("close", 0)),
            volume=float(data.get("volume", 0)),
            quote_asset_volume=float(data.get("quote_volume", 0)),
        )]
    
    def _get_rest_url(self) -> str:
        """Get the REST API URL for candles.
        
        :returns: REST API URL.
        """
        return f"{SPOT_REST_URL}{REST_CANDLES_ENDPOINT}"
    
    def _get_rest_params(
        self, 
        trading_pair: str, 
        interval: str, 
        start_time: Optional[int] = None, 
        end_time: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get REST API request parameters.
        
        :param trading_pair: Trading pair in standard format.
        :param interval: Interval string.
        :param start_time: Start time in seconds.
        :param end_time: End time in seconds.
        :param limit: Maximum number of candles to retrieve.
        :returns: Dictionary of request parameters.
        """
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": interval,
            "limit": limit if limit is not None else DEFAULT_CANDLES_LIMIT
        }

        if start_time is not None:
            params["start_time"] = self.convert_timestamp_to_exchange(start_time)

        if end_time is not None:
            params["end_time"] = self.convert_timestamp_to_exchange(end_time)

        return params
    
    def _parse_rest_response(self, response_data: Dict[str, Any]) -> List[CandleData]:
        """Process REST API response data into CandleData objects.
        
        :param response_data: Response data from the REST API.
        :returns: List of CandleData objects.
        """
        result = []
        
        # The mock server returns a standardized format
        if "status" in response_data and response_data["status"] == "ok":
            candles_data = response_data.get("data", [])
            
            for candle in candles_data:
                timestamp = candle.get("timestamp")
                
                # Convert timestamp to seconds
                timestamp = self.ensure_timestamp_in_seconds(timestamp)
                    
                result.append(
                    CandleData(
                        timestamp_raw=timestamp,
                        open=float(candle.get("open", 0)),
                        high=float(candle.get("high", 0)),
                        low=float(candle.get("low", 0)),
                        close=float(candle.get("close", 0)),
                        volume=float(candle.get("volume", 0)),
                        quote_asset_volume=float(candle.get("quote_volume", 0)),
                    )
                )
                
        return result
    
    def fetch_rest_candles_synchronous(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
    ) -> list[CandleData]:
        """Fetch candles using synchronous API calls.
        
        In a real implementation, this would make an HTTP request.
        For the mock adapter, we generate simulated candle data.
        
        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: List of CandleData objects
        """
        # Generate mock candle data
        current_time = start_time or 1620000000  # Example timestamp
        interval_seconds = INTERVALS.get(interval, 60)
        
        # Handle case where limit is None
        actual_limit = limit if limit is not None else 500
        
        candles = []
        for i in range(actual_limit):
            timestamp = current_time + (i * interval_seconds)
            candles.append({
                "timestamp": timestamp * 1000,  # Convert to milliseconds
                "open": 100.0 + i,
                "high": 101.0 + i,
                "low": 99.0 + i,
                "close": 100.5 + i,
                "volume": 1000.0 + i * 10,
                "quote_volume": 100500.0 + i * 100
            })
        
        # Create a response like what our mock server would return
        response = {
            "status": "ok",
            "data": candles
        }
        
        return self._parse_rest_response(response)
    
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles using asynchronous API calls.
        
        Unlike the SyncOnlyAdapter or AsyncOnlyAdapter, this implementation
        has custom implementations for both sync and async methods.
        
        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :param network_client: Optional network client to use
        :returns: List of CandleData objects
        """
        # Use the provided client, the instance client, or simulate one
        client = network_client or self._network_client
        if client:
            # In a real implementation, we'd use the client to make a request
            # For the mock adapter, we'll just generate test data with
            # a slightly different pattern than the sync method
            pass
            
        # Generate different mock candle data for async to demonstrate
        # that this is actually using the async implementation
        current_time = start_time or 1620000000  # Example timestamp
        interval_seconds = INTERVALS.get(interval, 60)
        
        # Handle case where limit is None
        actual_limit = limit if limit is not None else 500
        
        candles = []
        for i in range(actual_limit):
            timestamp = current_time + (i * interval_seconds)
            # Different price pattern to distinguish from sync method
            candles.append({
                "timestamp": timestamp * 1000,  # Convert to milliseconds
                "open": 200.0 + i * 2,
                "high": 205.0 + i * 2,
                "low": 195.0 + i * 2,
                "close": 202.5 + i * 2,
                "volume": 2000.0 + i * 20,
                "quote_volume": 405000.0 + i * 200
            })
        
        # Create a response like what our mock server would return
        response = {
            "status": "ok",
            "data": candles
        }
        
        return self._parse_rest_response(response)