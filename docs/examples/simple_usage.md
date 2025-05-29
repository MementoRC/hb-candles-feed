# Simple Usage Examples

This document provides examples of common usage patterns for the Candles Feed package.

## Basic REST API Example

The following example demonstrates how to fetch historical candle data using the REST API:

```python
import asyncio
import time
from candles_feed.core.candles_feed import CandlesFeed

async def main():
    # Create a feed for Binance BTC-USDT with 1-hour candles
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1h",
        max_records=24  # Keep last 24 hours
    )

    # Calculate time range for the last 24 hours
    end_time = int(time.time())
    start_time = end_time - (24 * 60 * 60)  # 24 hours ago

    # Fetch historical candles
    candles = await feed.fetch_candles(start_time=start_time, end_time=end_time)
    print(f"Fetched {len(candles)} candles")

    # Print details of the first and last candle
    if candles:
        first_candle = candles[0]
        last_candle = candles[-1]

        print("\nFirst candle:")
        print(f"Timestamp: {first_candle.timestamp}")
        print(f"Open: {first_candle.open}")
        print(f"High: {first_candle.high}")
        print(f"Low: {first_candle.low}")
        print(f"Close: {first_candle.close}")
        print(f"Volume: {first_candle.volume}")

        print("\nLast candle:")
        print(f"Timestamp: {last_candle.timestamp}")
        print(f"Open: {last_candle.open}")
        print(f"High: {last_candle.high}")
        print(f"Low: {last_candle.low}")
        print(f"Close: {last_candle.close}")
        print(f"Volume: {last_candle.volume}")

    # Get data as pandas DataFrame
    df = feed.get_candles_df()
    print("\nDataFrame summary:")
    print(df.describe())

    # Clean up resources
    await feed.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## WebSocket Streaming Example

This example shows how to stream real-time candle data using WebSockets:

```python
import asyncio
import logging
from candles_feed.core.candles_feed import CandlesFeed

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Create a feed with 1-minute candles
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        max_records=60  # Keep last 60 minutes
    )

    # Start WebSocket streaming
    await feed.start(strategy="websocket")
    logger.info("WebSocket feed started")

    # Monitor for updates
    try:
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 60:  # Run for 1 minute
            candles = feed.get_candles()
            if candles:
                latest = candles[-1]
                logger.info(
                    f"Latest candle: timestamp={latest.timestamp}, "
                    f"open={latest.open}, high={latest.high}, "
                    f"low={latest.low}, close={latest.close}, "
                    f"volume={latest.volume}"
                )
            await asyncio.sleep(5)  # Check every 5 seconds
    finally:
        # Always clean up resources
        await feed.stop()
        logger.info("WebSocket feed stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

## Multi-Exchange Example

This example demonstrates how to work with multiple exchanges simultaneously:

```python
import asyncio
import logging
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.exchange_registry import ExchangeRegistry

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # List available exchange adapters
    ExchangeRegistry.discover_adapters()
    exchanges = ExchangeRegistry.list_available_adapters()
    logger.info(f"Available exchanges: {exchanges}")

    # Create feeds for different exchanges with the same trading pair
    feeds = []
    exchange_names = ["binance_spot", "kucoin_spot", "coinbase_advanced_trade"]

    for exchange in exchange_names:
        if exchange in exchanges:
            try:
                feed = CandlesFeed(
                    exchange=exchange,
                    trading_pair="BTC-USDT",  # Note: May be BTC-USD on some exchanges
                    interval="1m",
                    max_records=10
                )
                feeds.append((exchange, feed))
                logger.info(f"Created feed for {exchange}")
            except Exception as e:
                logger.error(f"Error creating feed for {exchange}: {e}")

    # Start all feeds
    start_tasks = []
    for exchange, feed in feeds:
        start_tasks.append(feed.start())

    await asyncio.gather(*start_tasks)
    logger.info("All feeds started")

    # Wait for data to arrive
    await asyncio.sleep(10)

    # Compare prices across exchanges
    logger.info("\nCurrent BTC prices across exchanges:")
    for exchange, feed in feeds:
        candles = feed.get_candles()
        if candles:
            latest = candles[-1]
            logger.info(f"{exchange}: close={latest.close}, volume={latest.volume}")
        else:
            logger.warning(f"{exchange}: No data received")

    # Stop all feeds
    stop_tasks = []
    for _, feed in feeds:
        stop_tasks.append(feed.stop())

    await asyncio.gather(*stop_tasks)
    logger.info("All feeds stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

## Data Analysis Example

This example shows how to perform basic analysis on candle data:

```python
import asyncio
import pandas as pd
import numpy as np
from candles_feed.core.candles_feed import CandlesFeed

async def main():
    # Create a feed with hourly candles for the last week
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1h",
        max_records=168  # 24 hours * 7 days
    )

    # Fetch historical data
    await feed.fetch_candles()

    # Get data as DataFrame
    df = feed.get_candles_df()
    if df.empty:
        print("No data received")
        await feed.stop()
        return

    # Convert timestamp to datetime for better readability
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')

    # Calculate basic technical indicators
    # 1. Simple Moving Averages
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()

    # 2. Exponential Moving Average
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()

    # 3. Bollinger Bands
    window = 20
    df['middle_band'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['upper_band'] = df['middle_band'] + 2 * df['std']
    df['lower_band'] = df['middle_band'] - 2 * df['std']

    # 4. Relative Strength Index (RSI)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # 5. MACD
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['signal']

    # Display analysis results
    print("\nAnalysis of BTC-USDT price data:")
    print(f"Period: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    print(f"Number of candles: {len(df)}")
    print(f"Price range: {df['low'].min()} - {df['high'].max()}")
    print(f"Average volume: {df['volume'].mean():.2f}")

    print("\nLatest indicators:")
    latest = df.iloc[-1]
    print(f"Price: {latest['close']}")
    print(f"SMA (20): {latest['sma_20']}")
    print(f"EMA (20): {latest['ema_20']}")
    print(f"Bollinger Bands: {latest['lower_band']:.2f} - {latest['middle_band']:.2f} - {latest['upper_band']:.2f}")
    print(f"RSI: {latest['rsi']:.2f}")
    print(f"MACD: {latest['macd']:.2f}, Signal: {latest['signal']:.2f}, Histogram: {latest['macd_histogram']:.2f}")

    # Clean up
    await feed.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Handling Example

This example demonstrates robust error handling:

```python
import asyncio
import logging
import time
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.exchange_registry import ExchangeRegistry

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_with_retry(exchange, trading_pair, interval, retries=3):
    """Fetch candle data with retry logic."""
    feed = None
    try:
        feed = CandlesFeed(
            exchange=exchange,
            trading_pair=trading_pair,
            interval=interval,
            max_records=100
        )

        # Try to fetch data with retries
        attempt = 0
        success = False

        while attempt < retries and not success:
            attempt += 1
            try:
                logger.info(f"Attempt {attempt} to fetch candles for {trading_pair} on {exchange}")
                candles = await feed.fetch_candles()

                if candles and len(candles) > 0:
                    logger.info(f"Successfully fetched {len(candles)} candles")
                    success = True
                    return candles
                else:
                    logger.warning(f"No candles received on attempt {attempt}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Error fetching candles (attempt {attempt}): {e}")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        if not success:
            logger.error(f"Failed to fetch candles after {retries} attempts")
            return []

    except Exception as e:
        logger.error(f"Error creating feed: {e}")
        return []
    finally:
        if feed:
            await feed.stop()

async def main():
    # Get available exchanges
    try:
        ExchangeRegistry.discover_adapters()
        exchanges = ExchangeRegistry.list_available_adapters()
        logger.info(f"Available exchanges: {exchanges}")
    except Exception as e:
        logger.error(f"Error discovering adapters: {e}")
        return

    # Fetch data from multiple exchanges with error handling
    results = {}
    tasks = []

    for exchange in ["binance_spot", "kraken_spot", "non_existent_exchange"]:
        if exchange in exchanges or exchange == "non_existent_exchange":
            task = asyncio.create_task(
                fetch_with_retry(
                    exchange=exchange,
                    trading_pair="BTC-USDT",
                    interval="1h"
                )
            )
            tasks.append((exchange, task))

    # Wait for all tasks to complete
    for exchange, task in tasks:
        try:
            candles = await task
            results[exchange] = candles
        except Exception as e:
            logger.error(f"Error in task for {exchange}: {e}")
            results[exchange] = []

    # Display results
    for exchange, candles in results.items():
        if candles:
            logger.info(f"{exchange}: Successfully fetched {len(candles)} candles")
        else:
            logger.warning(f"{exchange}: No candles fetched")

if __name__ == "__main__":
    asyncio.run(main())
```

## Real-time Trading Signal Example

This example demonstrates how to generate simple trading signals from real-time data:

```python
import asyncio
import logging
from candles_feed.core.candles_feed import CandlesFeed

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleStrategy:
    """A simple trading strategy using moving averages."""

    def __init__(self, short_window=5, long_window=20):
        self.short_window = short_window
        self.long_window = long_window
        self.positions = []  # Track positions: 1 for long, -1 for short, 0 for neutral

    def calculate_signals(self, df):
        """Calculate trading signals based on moving average crossover."""
        if len(df) < self.long_window:
            return "INSUFFICIENT_DATA"

        # Calculate moving averages
        df['short_ma'] = df['close'].rolling(window=self.short_window).mean()
        df['long_ma'] = df['close'].rolling(window=self.long_window).mean()

        # Current position
        current_position = 0
        if len(self.positions) > 0:
            current_position = self.positions[-1]

        # Get the last two rows to check for a crossover
        if len(df) >= 2:
            prev_row = df.iloc[-2]
            curr_row = df.iloc[-1]

            # Check for crossing conditions
            prev_crossing = prev_row['short_ma'] > prev_row['long_ma']
            curr_crossing = curr_row['short_ma'] > curr_row['long_ma']

            # Generate signals
            if not prev_crossing and curr_crossing:  # Bullish crossover
                if current_position <= 0:
                    self.positions.append(1)
                    return "BUY"
            elif prev_crossing and not curr_crossing:  # Bearish crossover
                if current_position >= 0:
                    self.positions.append(-1)
                    return "SELL"

        self.positions.append(current_position)
        return "HOLD"

async def main():
    # Create a feed for real-time data
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        max_records=30  # Keep enough for our strategy
    )

    # Initialize our strategy
    strategy = SimpleStrategy(short_window=5, long_window=20)

    # Start the feed
    await feed.start(strategy="websocket")
    logger.info("Started real-time feed")

    try:
        # Run for a limited time (5 minutes)
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < 300:
            # Get latest data
            df = feed.get_candles_df()

            if not df.empty and len(df) >= strategy.long_window:
                # Calculate signals
                signal = strategy.calculate_signals(df)

                # Log signal and current price
                latest_price = df.iloc[-1]['close']
                logger.info(f"Signal: {signal}, Price: {latest_price}")

                if signal == "BUY":
                    logger.info(f"BUY SIGNAL at {latest_price}")
                elif signal == "SELL":
                    logger.info(f"SELL SIGNAL at {latest_price}")

            # Wait for next update
            await asyncio.sleep(10)

    finally:
        # Clean up
        await feed.stop()
        logger.info("Stopped feed")

if __name__ == "__main__":
    asyncio.run(main())
```

These examples demonstrate the core functionality of the Candles Feed package. You can adapt and extend them based on your specific requirements.
