"""
Candle data model for the mock exchange server.
"""

import random
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class MockCandleData:
    """
    Candle data structure for mock exchange data.
    
    This is a standardized representation of candle data used by the mock server.
    Each exchange adapter will convert between this format and their exchange-specific format.
    """
    timestamp: int  # Unix timestamp in seconds
    open: float
    high: float 
    low: float
    close: float
    volume: float
    quote_asset_volume: float
    n_trades: int
    taker_buy_base_volume: float
    taker_buy_quote_volume: float
    
    @property
    def timestamp_ms(self) -> int:
        """Return timestamp in milliseconds."""
        return self.timestamp * 1000
    
    @classmethod
    def create_random(cls, timestamp: int, previous_candle: Optional['MockCandleData'] = None, 
                      base_price: float = 50000.0, volatility: float = 0.01) -> 'MockCandleData':
        """
        Create a random candle, optionally based on a previous candle.
        
        Args:
            timestamp: Unix timestamp in seconds
            previous_candle: Previous candle to base price movements on
            base_price: Base price if no previous candle is provided
            volatility: Price volatility as a decimal percentage (0.01 = 1%)
            
        Returns:
            A new MockCandleData instance with random but realistic values
        """
        if previous_candle:
            # Base the new candle on the previous close price
            base_price = previous_candle.close
        
        # Generate price movement
        price_change = (random.random() - 0.5) * 2 * volatility * base_price
        close_price = base_price + price_change
        
        # Create a realistic OHLC pattern
        price_range = abs(price_change) * 1.5
        open_price = base_price
        high_price = max(open_price, close_price) + (random.random() * price_range * 0.5)
        low_price = min(open_price, close_price) - (random.random() * price_range * 0.5)
        
        # Generate volume data
        volume = 10.0 + (random.random() * 20.0)
        quote_volume = volume * ((open_price + close_price) / 2)
        
        # Taker volume (typically 40-60% of total volume)
        taker_ratio = 0.4 + (random.random() * 0.2)
        taker_base_volume = volume * taker_ratio
        taker_quote_volume = taker_base_volume * ((open_price + close_price) / 2)
        
        # Number of trades - correlates somewhat with volume
        n_trades = int(50 + (volume * 5) + (random.random() * 50))
        
        return cls(
            timestamp=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            quote_asset_volume=quote_volume,
            n_trades=n_trades,
            taker_buy_base_volume=taker_base_volume,
            taker_buy_quote_volume=taker_quote_volume
        )
    
    @classmethod
    def from_candle_data(cls, candle_data):
        """
        Convert a CandleData object from the main package to a MockCandleData object.
        
        This allows using real data in the mock server for testing.
        
        Args:
            candle_data: A CandleData object from the candles_feed.core.candle_data module
            
        Returns:
            A MockCandleData instance
        """
        try:
            # Use the timestamp attribute if available, otherwise use timestamp_raw
            timestamp = getattr(candle_data, 'timestamp', None)
            if timestamp is None:
                timestamp = getattr(candle_data, 'timestamp_raw', int(time.time()))
            
            return cls(
                timestamp=timestamp,
                open=candle_data.open,
                high=candle_data.high,
                low=candle_data.low,
                close=candle_data.close,
                volume=candle_data.volume,
                quote_asset_volume=candle_data.quote_asset_volume,
                n_trades=candle_data.n_trades,
                taker_buy_base_volume=candle_data.taker_buy_base_volume,
                taker_buy_quote_volume=candle_data.taker_buy_quote_volume
            )
        except AttributeError as e:
            # If the structure is different, try to adapt as best as possible
            return cls.create_random(
                timestamp=int(time.time()),
                base_price=getattr(candle_data, 'close', 50000.0)
            )
