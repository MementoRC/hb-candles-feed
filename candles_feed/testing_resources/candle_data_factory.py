"""
Factory for generating candle data for testing purposes.

This module provides utilities to create realistic candle data for testing
without relying on actual exchange connections.
"""

import random
from typing import List, Optional, Tuple

from candles_feed.core.candle_data import CandleData


class CandleDataFactory:
    """Factory class for generating realistic candle data for testing."""

    @staticmethod
    def create_random(
        timestamp: int,
        previous_candle: Optional[CandleData] = None,
        base_price: float = 50000.0,
        volatility: float = 0.01,
    ) -> CandleData:
        """
        Create a random candle, optionally based on a previous candle.

        Args:
            timestamp: Unix timestamp in seconds
            previous_candle: Previous candle to base price movements on
            base_price: Base price if no previous candle is provided
            volatility: Price volatility as a decimal percentage (0.01 = 1%)

        Returns:
            A new CandleData instance with random but realistic values
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

        return CandleData(
            timestamp_raw=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            quote_asset_volume=quote_volume,
            n_trades=n_trades,
            taker_buy_base_volume=taker_base_volume,
            taker_buy_quote_volume=taker_quote_volume,
        )

    @staticmethod
    def create_trending_series(
        start_timestamp: int,
        count: int,
        interval_seconds: int,
        start_price: float = 50000.0,
        trend: float = 0.001,
        volatility: float = 0.005,
    ) -> List[CandleData]:
        """
        Create a series of candles with an underlying trend.

        Args:
            start_timestamp: Starting timestamp in seconds
            count: Number of candles to generate
            interval_seconds: Time between candles in seconds
            start_price: Starting price
            trend: Price trend as a decimal percentage per candle (0.001 = 0.1%)
            volatility: Random price volatility as a decimal percentage (0.005 = 0.5%)

        Returns:
            List of CandleData instances with a trending price pattern
        """
        candles = []
        current_price = start_price

        for i in range(count):
            timestamp = start_timestamp + (i * interval_seconds)

            # Add trend component
            trend_factor = 1.0 + trend
            current_price *= trend_factor

            # Create candle with current base price
            previous_candle = candles[-1] if candles else None
            candle = CandleDataFactory.create_random(
                timestamp=timestamp,
                previous_candle=previous_candle,
                base_price=current_price,
                volatility=volatility,
            )
            candles.append(candle)

            # Update price for next iteration
            current_price = candle.close

        return candles

    @staticmethod
    def create_price_event(
        candles: List[CandleData], event_index: int, event_magnitude: float = 0.05
    ) -> List[CandleData]:
        """
        Create a significant price event (spike or drop) at a specific index.

        Args:
            candles: Existing list of candles to modify
            event_index: Index at which to create the price event
            event_magnitude: Size of price change as a decimal percentage (0.05 = 5%)

        Returns:
            Modified list of candles with the price event
        """
        if not candles or event_index >= len(candles):
            return candles

        # Determine if it's a price spike (positive) or drop (negative)
        is_spike = random.random() > 0.5
        magnitude = event_magnitude if is_spike else -event_magnitude

        # Get the candle to modify
        candle = candles[event_index]
        base_price = candle.open

        # Calculate the new price after the event
        event_change = base_price * magnitude
        new_close = base_price + event_change

        # Create new high/low values
        new_high = max(candle.high, new_close, base_price)
        new_low = min(candle.low, new_close, base_price)

        # Generate higher volume for the event
        volume_multiplier = 1.5 + (random.random() * 1.5)  # 1.5x to 3x normal volume
        new_volume = candle.volume * volume_multiplier

        # Create a new candle with the price event
        updated_candle = CandleData(
            timestamp_raw=candle.timestamp,
            open=base_price,
            high=new_high,
            low=new_low,
            close=new_close,
            volume=new_volume,
            quote_asset_volume=new_volume * ((base_price + new_close) / 2),
            n_trades=int(candle.n_trades * volume_multiplier),
            taker_buy_base_volume=candle.taker_buy_base_volume * volume_multiplier,
            taker_buy_quote_volume=candle.taker_buy_quote_volume * volume_multiplier,
        )

        # Replace the candle at the event index
        result = candles.copy()
        result[event_index] = updated_candle

        # Update subsequent candles to reflect the new price level
        if event_index < len(result) - 1:
            subsequent_base = updated_candle.close
            for i in range(event_index + 1, len(result)):
                # Create a new candle based on the updated price level
                result[i] = CandleDataFactory.create_random(
                    timestamp=result[i].timestamp, base_price=subsequent_base, volatility=0.01
                )
                subsequent_base = result[i].close

        return result

    @staticmethod
    def create_market_simulation(
        start_timestamp: int, count: int, interval_seconds: int, initial_price: float = 50000.0
    ) -> List[CandleData]:
        """
        Create a realistic market simulation with trends and volatility events.

        Args:
            start_timestamp: Starting timestamp in seconds
            count: Number of candles to generate
            interval_seconds: Time between candles in seconds
            initial_price: Starting price

        Returns:
            List of CandleData instances simulating realistic market behavior
        """
        # First create a base trend (randomly bullish or bearish)
        trend = (random.random() - 0.4) * 0.002  # -0.04% to +0.16% per candle
        candles = CandleDataFactory.create_trending_series(
            start_timestamp=start_timestamp,
            count=count,
            interval_seconds=interval_seconds,
            start_price=initial_price,
            trend=trend,
            volatility=0.005,
        )

        # Add some price events (1-3 significant moves)
        num_events = random.randint(1, 3)
        for _ in range(num_events):
            # Don't place events too close to the start or end
            buffer = max(5, count // 10)
            event_index = random.randint(buffer, count - buffer - 1)
            event_magnitude = 0.02 + (random.random() * 0.08)  # 2% to 10% price event
            candles = CandleDataFactory.create_price_event(
                candles=candles, event_index=event_index, event_magnitude=event_magnitude
            )

        return candles
