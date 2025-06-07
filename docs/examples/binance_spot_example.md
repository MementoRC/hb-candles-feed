# Binance Spot Example

This example demonstrates how to use the Candles Feed framework with Binance Spot exchange. It shows the basic setup and usage patterns for fetching and working with candle data.

## Prerequisites

Before running this example, make sure you have installed the Candles Feed package:

```bash
pip install hummingbot-candles-feed
```

## Basic Usage

```python
import asyncio
from candles_feed.core.candles_feed import CandlesFeed

async def main():
    """Simple example using Binance Spot."""
    # Create a CandlesFeed instance for Binance Spot
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        max_records=100
    )

    try:
        # Fetch historical candles
        print("Fetching historical candles...")
        candles = await feed.fetch_candles()
        print(f"Fetched {len(candles)} candles")

        # Start real-time updates (using WebSocket by default)
        print("Starting real-time updates...")
        await feed.start()

        # Wait for some data to accumulate
        for i in range(5):
            print(f"Waiting... ({i+1}/5)")
            await asyncio.sleep(10)

            # Get the current candles
            candles = feed.get_candles()
            if candles:
                latest = candles[-1]
                print(f"Latest price: {latest.close} (timestamp: {latest.timestamp})")

    finally:
        # Always stop the feed when done
        print("Stopping feed...")
        await feed.stop()
        print("Feed stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

## Using Pandas DataFrame

The Candles Feed framework provides a convenient method to convert candle data to a pandas DataFrame:

```python
import asyncio
import pandas as pd
from candles_feed.core.candles_feed import CandlesFeed

async def analyze_btc():
    """Example showing DataFrame conversion and analysis."""
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1h",  # 1-hour candles
        max_records=24  # Last 24 hours
    )

    try:
        # Fetch historical data
        await feed.fetch_candles()

        # Convert to DataFrame
        df = feed.get_candles_df()

        # Basic analysis
        print(f"Data points: {len(df)}")
        print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"Price range: ${df['low'].min()} - ${df['high'].max()}")
        print(f"Average volume: {df['volume'].mean():.2f}")

        # Calculate simple moving averages
        df['SMA_5'] = df['close'].rolling(5).mean()
        df['SMA_10'] = df['close'].rolling(10).mean()

        # Print the latest values
        latest = df.iloc[-1]
        print(f"Latest close: ${latest['close']}")
        print(f"5-period SMA: ${latest['SMA_5']}")
        print(f"10-period SMA: ${latest['SMA_10']}")

    finally:
        await feed.stop()

if __name__ == "__main__":
    asyncio.run(analyze_btc())
```

## Working with Multiple Trading Pairs

This example shows how to fetch data for multiple trading pairs simultaneously:

```python
import asyncio
from candles_feed.core.candles_feed import CandlesFeed

async def monitor_crypto_markets():
    """Monitor multiple crypto trading pairs."""
    # Define the pairs to monitor
    pairs = [
        ("BTC-USDT", "Bitcoin"),
        ("ETH-USDT", "Ethereum"),
        ("SOL-USDT", "Solana"),
        ("BNB-USDT", "Binance Coin")
    ]

    # Create feeds for each pair
    feeds = {}
    for pair, name in pairs:
        feeds[pair] = {
            "name": name,
            "feed": CandlesFeed(
                exchange="binance_spot",
                trading_pair=pair,
                interval="5m",
                max_records=12
            )
        }

    try:
        # Start all feeds
        for pair_info in feeds.values():
            await pair_info["feed"].fetch_candles()
            await pair_info["feed"].start(strategy="websocket")

        # Monitor for a period
        for i in range(5):
            print(f"\n--- Update {i+1} ---")

            # Print current prices for all pairs
            for pair, pair_info in feeds.items():
                feed = pair_info["feed"]
                name = pair_info["name"]

                candles = feed.get_candles()
                if candles:
                    latest = candles[-1]
                    price = latest.close
                    change = ((price / candles[0].close) - 1) * 100

                    print(f"{name}: ${price:.2f} ({change:+.2f}%)")

            await asyncio.sleep(60)  # Wait for 1 minute

    finally:
        # Stop all feeds
        for pair_info in feeds.values():
            await pair_info["feed"].stop()

if __name__ == "__main__":
    asyncio.run(monitor_crypto_markets())
```

## REST-Only Mode

If you prefer to use REST API instead of WebSocket (e.g., for lower resource usage or specific interval requirements):

```python
import asyncio
from candles_feed.core.candles_feed import CandlesFeed

async def main():
    """Example using REST polling only."""
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="15m",  # 15-minute candles
        max_records=20
    )

    try:
        # Start with REST polling strategy
        await feed.start(strategy="polling")

        # Monitor for a while
        for i in range(3):
            print(f"Polling iteration {i+1}")
            candles = feed.get_candles()
            if candles:
                latest = candles[-1]
                print(f"Latest candle: OHLC = {latest.open}/{latest.high}/{latest.low}/{latest.close}")

            # Wait for next poll
            await asyncio.sleep(30)

    finally:
        await feed.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Handling

It's important to implement proper error handling in your application:

```python
import asyncio
import logging
from candles_feed.core.candles_feed import CandlesFeed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Example with error handling."""
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m"
    )

    try:
        # Attempt to start the feed
        try:
            await feed.start()
            logger.info("Feed started successfully")
        except Exception as e:
            logger.error(f"Failed to start feed: {str(e)}")
            return

        # Monitor and handle potential errors
        try:
            for i in range(10):
                candles = feed.get_candles()
                if candles:
                    logger.info(f"Current price: {candles[-1].close}")
                else:
                    logger.warning("No candle data available")

                await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error during monitoring: {str(e)}")

    finally:
        # Always attempt to stop the feed
        try:
            await feed.stop()
            logger.info("Feed stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping feed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
```

## See Also

For more examples and details, check out:

- [Simple Usage Guide](simple_usage.md) - For a more basic introduction
- [Mock Server Example](mock_server_example.md) - For testing without connecting to real exchanges
- [Adapters Overview](../adapters/overview.md) - For information on other supported exchanges
- [API Reference](../api_reference/core.md) - For detailed API documentation
