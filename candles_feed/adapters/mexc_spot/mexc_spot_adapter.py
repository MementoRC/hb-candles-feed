"""
MEXC spot exchange adapter for the Candle Feed framework.
"""

from typing import List, Optional

from candles_feed.adapters.mexc.constants import INTERVAL_TO_MEXC_FORMAT
from candles_feed.adapters.mexc.mexc_base_adapter import MEXCBaseAdapter
from candles_feed.adapters.mexc_spot.constants import (
    CANDLES_ENDPOINT,
    KLINE_TOPIC,
    REST_URL,
    WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("mexc_spot")
class MEXCSpotAdapter(MEXCBaseAdapter):
    """MEXC spot exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        return WSS_URL
        
    def get_kline_topic(self) -> str:
        """Get WebSocket kline topic prefix.
        
        Returns:
            Kline topic prefix string
        """
        return KLINE_TOPIC
    
    def get_interval_format(self, interval: str) -> str:
        """Get exchange-specific interval format.
        
        Args:
            interval: Standard interval format
            
        Returns:
            Exchange-specific interval format
        """
        return INTERVAL_TO_MEXC_FORMAT.get(interval, interval)

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
            limit: Maximum number of candles to return

        Returns:
            Dictionary of parameters for REST API request
        """
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": interval
        }
        
        if limit:
            params["limit"] = limit
        
        if start_time:
            params["startTime"] = start_time * 1000  # Convert to milliseconds
        if end_time:
            params["endTime"] = end_time * 1000      # Convert to milliseconds
            
        return params

    def parse_rest_response(self, data: Optional[list]) -> List[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        if data is None:
            return []
            
        # MEXC REST API format is similar to Binance
        # [
        #   [
        #     1499040000000,      // Open time
        #     "0.01634790",       // Open
        #     "0.80000000",       // High
        #     "0.01575800",       // Low
        #     "0.01577100",       // Close
        #     "148976.11427815",  // Volume
        #     1499644799999,      // Close time
        #     "2434.19055334",    // Quote asset volume
        #     308,                // Number of trades
        #     "1756.87402397",    // Taker buy base asset volume
        #     "28.46694368",      // Taker buy quote asset volume
        #   ]
        # ]
            
        candles = []
        for row in data:
            if len(row) < 11:  # Make sure we have enough data
                continue
                
            candles.append(CandleData(
                timestamp_raw=row[0] / 1000,  # Convert from milliseconds
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_asset_volume=float(row[7]),
                n_trades=int(row[8]),
                taker_buy_base_volume=float(row[9]),
                taker_buy_quote_volume=float(row[10])
            ))
        return candles

    def parse_ws_message(self, data: Optional[dict]) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        if data is None:
            return None
            
        # Check if we have a candle update
        if "d" in data and "c" in data.get("d", {}):
            candle = data["d"]
            
            try:
                timestamp = int(candle.get("t", 0)) / 1000  # Convert from milliseconds
                return [CandleData(
                    timestamp_raw=timestamp,
                    open=float(candle.get("o", 0.0)),
                    high=float(candle.get("h", 0.0)),
                    low=float(candle.get("l", 0.0)),
                    close=float(candle.get("c", 0.0)),
                    volume=float(candle.get("v", 0.0)),
                    quote_asset_volume=float(candle.get("qv", 0.0)),
                    n_trades=int(candle.get("n", 0)),
                    taker_buy_base_volume=0.0,  # Not available in websocket
                    taker_buy_quote_volume=0.0   # Not available in websocket
                )]
            except (ValueError, TypeError):
                pass
                
        return None