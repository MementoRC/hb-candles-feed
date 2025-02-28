"""
Coinbase Advanced Trade adapter for the Candle Feed framework.
"""

from typing import Dict, List, Optional

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.coinbase_advanced_trade.constants import (
    BASE_REST_URL, INTERVALS, WSS_URL, WS_INTERVALS, MAX_CANDLES_SIZE
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("coinbase_advanced_trade")
class CoinbaseAdvancedTradeAdapter(BaseAdapter):
    """Coinbase Advanced Trade exchange adapter."""
    
    def get_trading_pair_format(self, trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.
        
        Args:
            trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
            
        Returns:
            Trading pair in Coinbase format (same as standard)
        """
        # Coinbase uses the same format with hyphen
        return trading_pair
    
    def get_rest_url(self) -> str:
        """Get REST API URL for candles.
        
        Returns:
            REST API URL template (requires formatting with product_id)
        """
        return BASE_REST_URL
    
    def get_ws_url(self) -> str:
        """Get WebSocket URL.
        
        Returns:
            WebSocket URL
        """
        return WSS_URL
    
    def get_rest_params(self, 
                       trading_pair: str, 
                       interval: str, 
                       start_time: Optional[int] = None, 
                       end_time: Optional[int] = None, 
                       limit: Optional[int] = None) -> dict:
        """Get parameters for REST API request.
        
        Args:
            trading_pair: Trading pair
            interval: Candle interval
            start_time: Start time in seconds
            end_time: End time in seconds
            limit: Maximum number of candles to return (not used by Coinbase)
            
        Returns:
            Dictionary of parameters for REST API request
        """
        # Coinbase has different parameter names
        params = {
            "granularity": INTERVALS[interval]
        }
        
        if start_time is not None:
            params["start"] = start_time
        if end_time is not None:
            params["end"] = end_time
            
        return params
    
    def parse_rest_response(self, data: dict) -> List[CandleData]:
        """Parse REST API response into CandleData objects.
        
        Args:
            data: REST API response
            
        Returns:
            List of CandleData objects
        """
        # Coinbase candle format:
        # {
        #   "candles": [
        #     {
        #       "start": "2022-05-15T16:00:00Z",
        #       "low": "29288.38",
        #       "high": "29477.29",
        #       "open": "29405.34",
        #       "close": "29374.47",
        #       "volume": "142.0450069"
        #     },
        #     ...
        #   ]
        # }
        
        candles = []
        for candle in data.get("candles", []):
            candles.append(CandleData(
                timestamp_raw=candle.get("start", 0),
                open=float(candle.get("open", 0)),
                high=float(candle.get("high", 0)),
                low=float(candle.get("low", 0)),
                close=float(candle.get("close", 0)),
                volume=float(candle.get("volume", 0))
            ))
        return candles
    
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.
        
        Args:
            trading_pair: Trading pair
            interval: Candle interval
            
        Returns:
            WebSocket subscription payload
        """
        return {
            "type": "subscribe",
            "product_ids": [trading_pair],
            "channel": "candles",
            "granularity": INTERVALS[interval]
        }
    
    def parse_ws_message(self, data: dict) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.
        
        Args:
            data: WebSocket message
            
        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        # Coinbase WS candle format:
        # {
        #   "channel": "candles",
        #   "client_id": "...",
        #   "timestamp": "2023-02-14T17:02:36.346Z",
        #   "sequence_num": 1234,
        #   "events": [
        #     {
        #       "type": "candle",
        #       "candles": [
        #         {
        #           "start": "2023-02-14T17:01:00Z",
        #           "low": "22537.4",
        #           "high": "22540.7",
        #           "open": "22537.4",
        #           "close": "22540.7",
        #           "volume": "0.1360142"
        #         }
        #       ]
        #     }
        #   ]
        # }
        
        if not isinstance(data, dict) or "events" not in data:
            return None
            
        candles = []
        for event in data["events"]:
            if not isinstance(event, dict) or "candles" not in event:
                continue
                
            for candle in event.get("candles", []):
                candles.append(CandleData(
                    timestamp_raw=candle.get("start", 0),
                    open=float(candle.get("open", 0)),
                    high=float(candle.get("high", 0)),
                    low=float(candle.get("low", 0)),
                    close=float(candle.get("close", 0)),
                    volume=float(candle.get("volume", 0))
                ))
                
        return candles if candles else None
        
    def get_supported_intervals(self) -> Dict[str, int]:
        """Get supported intervals and their durations in seconds.
        
        Returns:
            Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS
        
    def get_ws_supported_intervals(self) -> List[str]:
        """Get intervals supported by WebSocket API.
        
        Returns:
            List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS