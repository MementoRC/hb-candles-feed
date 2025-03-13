# Quick Start Guide

This guide will help you get started with the Candles Feed framework quickly. You'll learn how to:

1. Create a candles feed
2. Fetch real-time candle data
3. Access historical candles
4. Work with different exchanges

## Basic Usage

Here's a simple example of how to use the Candles Feed framework:

```python
import asyncio
import pandas as pd
from candles_feed import CandlesFeed
from candles_feed.core.exchange_registry import ExchangeRegistry

async def main():
    # Discover available adapters
    ExchangeRegistry.discover_adapters()
    
    # Create a candles feed for Binance BTC-USDT pair with 1-minute candles
    adapter = ExchangeRegistry.get_adapter("binance_spot")
    candles_feed = CandlesFeed(
        adapter=adapter,
        trading_pair="BTC-USDT",
        interval="1m",
        max_records=100
    )
    
    # Start the feed
    await candles_feed.start()
    
    # Wait for the feed to be ready
    print("Waiting for candles data...")
    while not candles_feed.ready:
        await asyncio.sleep(1)
        
    # Get the candles as a pandas DataFrame
    df = candles_feed.get_candles_df()
    
    # Display the data
    print("\nCandle Data:")
    print(df.tail())
    
    # Keep receiving real-time updates for a while
    print("\nReceiving real-time updates for 30 seconds...")
    await asyncio.sleep(30)
    
    # Get the updated candles
    updated_df = candles_feed.get_candles_df()
    print("\nUpdated Candle Data:")
    print(updated_df.tail())
    
    # Stop the feed
    await candles_feed.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Selecting an Exchange

The framework supports multiple exchanges. To see available exchanges:

```python
from candles_feed.core.exchange_registry import ExchangeRegistry

# Discover available adapters
ExchangeRegistry.discover_adapters()

# List all available exchanges
available_exchanges = ExchangeRegistry.list_available_adapters()
print(f"Available exchanges: {available_exchanges}")
```

To create a feed for a specific exchange, get the appropriate adapter:

```python
# For Binance
adapter = ExchangeRegistry.get_adapter("binance_spot")

# For Coinbase Advanced Trade
adapter = ExchangeRegistry.get_adapter("coinbase_advanced_trade")

# For Kraken
adapter = ExchangeRegistry.get_adapter("kraken_spot")

# For KuCoin
adapter = ExchangeRegistry.get_adapter("kucoin_spot")

# For OKX
adapter = ExchangeRegistry.get_adapter("okx_spot")

# For Bybit
adapter = ExchangeRegistry.get_adapter("bybit_spot")
```

## Supported Intervals

Different exchanges support different candle intervals. To check supported intervals:

```python
adapter = ExchangeRegistry.get_adapter("binance_spot")
intervals = adapter.get_supported_intervals()
print(f"Supported intervals: {list(intervals.keys())}")
```

Common intervals include:
- `"1m"`: 1 minute
- `"5m"`: 5 minutes
- `"15m"`: 15 minutes
- `"1h"`: 1 hour
- `"4h"`: 4 hours
- `"1d"`: 1 day

## Fetching Historical Data

To fetch historical candle data for a specific time range:

```python
import time
from datetime import datetime, timedelta

# Get timestamps for last 24 hours
end_time = int(time.time())
start_time = end_time - (24 * 60 * 60)  # 24 hours ago

# Fetch historical data
historical_df = await candles_feed.fetch_historical_candles(
    start_time=start_time,
    end_time=end_time
)

print(f"Historical data: {len(historical_df)} candles")
print(historical_df.head())
```

## Working with Multiple Feeds

You can create multiple feeds for different trading pairs or exchanges:

```python
async def main():
    # Discover available adapters
    ExchangeRegistry.discover_adapters()
    
    # Create feeds for different trading pairs
    btc_feed = CandlesFeed(
        adapter=ExchangeRegistry.get_adapter("binance_spot"),
        trading_pair="BTC-USDT",
        interval="1m"
    )
    
    eth_feed = CandlesFeed(
        adapter=ExchangeRegistry.get_adapter("binance_spot"),
        trading_pair="ETH-USDT",
        interval="1m"
    )
    
    # Start both feeds
    await asyncio.gather(
        btc_feed.start(),
        eth_feed.start()
    )
    
    # Wait for data
    while not (btc_feed.ready and eth_feed.ready):
        await asyncio.sleep(1)
        
    # Compare data
    btc_df = btc_feed.get_candles_df()
    eth_df = eth_feed.get_candles_df()
    
    print("BTC-USDT latest price:", btc_df.iloc[-1]["close"])
    print("ETH-USDT latest price:", eth_df.iloc[-1]["close"])
    
    # Stop feeds
    await asyncio.gather(
        btc_feed.stop(),
        eth_feed.stop()
    )
```

## Data Analysis Example

Here's how to perform basic analysis on the candle data:

```python
import pandas as pd
import matplotlib.pyplot as plt

async def analyze_data():
    # Create and start a feed
    adapter = ExchangeRegistry.get_adapter("binance_spot")
    feed = CandlesFeed(
        adapter=adapter,
        trading_pair="BTC-USDT",
        interval="1h",
        max_records=168  # Last 7 days of hourly data
    )
    
    await feed.start()
    
    # Wait for data
    while not feed.ready:
        await asyncio.sleep(1)
        
    # Get the data
    df = feed.get_candles_df()
    
    # Convert timestamp to datetime
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    df.set_index('datetime', inplace=True)
    
    # Calculate some indicators
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # Plot the data
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['close'], label='Close Price')
    plt.plot(df.index, df['sma_20'], label='20-period SMA')
    plt.plot(df.index, df['ema_50'], label='50-period EMA')
    plt.legend()
    plt.title('BTC-USDT Price with Moving Averages')
    plt.savefig('btc_analysis.png')
    
    # Stop the feed
    await feed.stop()
```

## Working with Different Strategies

The framework automatically selects the best strategy (WebSocket or REST polling) based on exchange capabilities:

```python
from candles_feed.core.collection_strategies import WebSocketStrategy, RESTPollingStrategy


def check_strategy(candles_feed):
    """Check which network strategy is being used."""
    if isinstance(candles_feed._network_strategy, WebSocketStrategy):
        print("Using WebSocket strategy for real-time updates")
    elif isinstance(candles_feed._network_strategy, RESTPollingStrategy):
        print("Using REST polling strategy for updates")
    else:
        print(f"Using unknown strategy: {type(candles_feed._network_strategy)}")
```

## Error Handling

Here's how to handle common errors:

```python
try:
    adapter = ExchangeRegistry.get_adapter("unknown_exchange")
except ValueError as e:
    print(f"Exchange not found: {e}")

try:
    await feed.start()
    # Wait for data with timeout
    start_time = time.time()
    while not feed.ready and time.time() - start_time < 30:
        await asyncio.sleep(1)
        
    if not feed.ready:
        print("Timed out waiting for data")
except Exception as e:
    print(f"Error starting feed: {e}")
finally:
    await feed.stop()
```

## Next Steps

Now that you have a basic understanding of how to use the Candles Feed framework, you can:

1. Learn about the architecture and core components
2. Explore the API Reference for detailed documentation
3. Learn how to [add support for new exchanges](../adapters/overview.md)