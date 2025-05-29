# Hummingbot Integration Example

This example demonstrates how to use the Candles Feed framework with Hummingbot's networking components.

## Basic Integration

Here's a simple example of integrating Candles Feed with Hummingbot's networking components:

```python
import asyncio
import logging

# Hummingbot imports
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.connections.connections_factory import ConnectionsFactory

# Candles Feed imports
from candles_feed import create_candles_feed_with_hummingbot


async def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("hummingbot_integration_example")

    # Set up Hummingbot's throttler with rate limits
    rate_limits = [
        # Binance rate limits
        {"limit_id": "binance_spot_klines", "limit": 1000, "time_interval": 60},
        {"limit_id": "binance_spot_ws", "limit": 5, "time_interval": 60},
    ]
    throttler = AsyncThrottler(rate_limits=rate_limits)

    # Set up Hummingbot's web assistants factory
    connections_factory = ConnectionsFactory()
    web_assistants_factory = WebAssistantsFactory(
        throttler=throttler,
        connections_factory=connections_factory
    )

    # Create a CandlesFeed instance with Hummingbot components
    logger.info("Creating CandlesFeed with Hummingbot components")
    candles_feed = create_candles_feed_with_hummingbot(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        throttler=throttler,
        web_assistants_factory=web_assistants_factory,
        logger=logger,
    )

    try:
        # Start the feed
        logger.info("Starting the feed")
        await candles_feed.start()

        # Wait for some candles to be collected
        logger.info("Waiting for candles to be collected...")
        await asyncio.sleep(5)

        # Get the candles as a DataFrame
        df = candles_feed.get_candles_df()
        logger.info(f"Collected {len(df)} candles")

        if not df.empty:
            # Display the latest price
            latest_candle = df.iloc[-1]
            logger.info(f"Latest price: {latest_candle['close']} (timestamp: {latest_candle['timestamp']})")

            # Use the data for analysis
            sma_20 = df['close'].rolling(20).mean().iloc[-1]
            logger.info(f"20-period SMA: {sma_20}")

    finally:
        # Always stop the feed to clean up resources
        logger.info("Stopping the feed")
        await candles_feed.stop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Example terminated by user")
    finally:
        loop.close()
```

## Integrating with a Hummingbot Strategy

Here's how to integrate Candles Feed with a Hummingbot strategy:

```python
from hummingbot.strategy.strategy_base import StrategyBase
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.connections.connections_factory import ConnectionsFactory
from hummingbot.data_feed import create_candles_feed_with_hummingbot


class CandlesBasedStrategy(StrategyBase):
    """A strategy that uses candle data for trading decisions."""

    def __init__(
        self,
        exchange: str,
        trading_pair: str,
        interval: str = "1m",
        max_records: int = 100,
        # ... other strategy parameters
    ):
        super().__init__()
        self._exchange = exchange
        self._trading_pair = trading_pair
        self._interval = interval
        self._max_records = max_records

        # Set up the throttler and web assistants factory
        self._throttler = AsyncThrottler(rate_limits=[
            # Add appropriate rate limits for your exchange
        ])
        self._connections_factory = ConnectionsFactory()
        self._web_assistants_factory = WebAssistantsFactory(
            throttler=self._throttler,
            connections_factory=self._connections_factory
        )

        # Create the candles feed
        self._candles_feed = create_candles_feed_with_hummingbot(
            exchange=self._exchange,
            trading_pair=self._trading_pair,
            interval=self._interval,
            max_records=self._max_records,
            throttler=self._throttler,
            web_assistants_factory=self._web_assistants_factory
        )

        # Strategy state
        self._ready = False

    async def start(self, clock, timestamp):
        """Start the strategy."""
        await super().start(clock, timestamp)
        self.logger().info("Starting strategy...")

        # Start the candles feed
        await self._candles_feed.start()

    async def stop(self, clock):
        """Stop the strategy."""
        self.logger().info("Stopping strategy...")

        # Stop the candles feed
        await self._candles_feed.stop()

        await super().stop(clock)

    async def tick(self, timestamp):
        """Process market data on each tick."""
        if not self._ready and self._candles_feed.ready:
            self._ready = True
            self.logger().info("Strategy ready with sufficient candle data")

        if not self._ready:
            return

        # Get the latest candle data
        df = self._candles_feed.get_candles_df()
        if len(df) < 20:  # Need at least 20 candles for analysis
            return

        # Calculate indicators
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()

        latest = df.iloc[-1]

        # Simple trading logic based on moving average crossover
        if df['sma_20'].iloc[-2] <= df['sma_50'].iloc[-2] and df['sma_20'].iloc[-1] > df['sma_50'].iloc[-1]:
            # Bullish crossover - buy signal
            self.logger().info(f"Bullish crossover detected at {latest['close']}")
            # Execute buy order
            # self.buy(...)

        elif df['sma_20'].iloc[-2] >= df['sma_50'].iloc[-2] and df['sma_20'].iloc[-1] < df['sma_50'].iloc[-1]:
            # Bearish crossover - sell signal
            self.logger().info(f"Bearish crossover detected at {latest['close']}")
            # Execute sell order
            # self.sell(...)
```

## Advanced Usage

### Combining Multiple Candle Feeds

You can use multiple candle feeds for cross-exchange analysis:

```python
async def analyze_cross_exchange():
    # Create the components
    throttler = AsyncThrottler(rate_limits=[...])
    web_assistants_factory = WebAssistantsFactory(throttler=throttler)

    # Create feeds for different exchanges
    binance_feed = create_candles_feed_with_hummingbot(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        throttler=throttler,
        web_assistants_factory=web_assistants_factory
    )

    coinbase_feed = create_candles_feed_with_hummingbot(
        exchange="coinbase_advanced_trade",
        trading_pair="BTC-USD",
        interval="1m",
        throttler=throttler,
        web_assistants_factory=web_assistants_factory
    )

    # Start both feeds
    await asyncio.gather(
        binance_feed.start(),
        coinbase_feed.start()
    )

    try:
        # Wait for data collection
        await asyncio.sleep(10)

        # Get data from both exchanges
        binance_df = binance_feed.get_candles_df()
        coinbase_df = coinbase_feed.get_candles_df()

        # Calculate price difference
        if not binance_df.empty and not coinbase_df.empty:
            binance_price = binance_df.iloc[-1]['close']
            coinbase_price = coinbase_df.iloc[-1]['close']

            diff_pct = (binance_price - coinbase_price) / coinbase_price * 100
            print(f"Price difference: {diff_pct:.2f}%")

            # Implement arbitrage logic based on price difference
    finally:
        # Stop both feeds
        await asyncio.gather(
            binance_feed.stop(),
            coinbase_feed.stop()
        )
```

### Using Different Network Strategies

You can specify which network strategy to use:

```python
# For high-frequency updates, use WebSocket when available
await candles_feed.start(strategy="websocket")

# For less frequent updates or when WebSockets are not reliable
await candles_feed.start(strategy="polling")

# Let the system decide based on exchange capabilities (default)
await candles_feed.start(strategy="auto")
```

### Fetching Historical Data

You can fetch historical data while using Hummingbot's rate limiting:

```python
import time
from datetime import datetime, timedelta

# Convert datetime to timestamp
end_time = int(time.time())
start_time = end_time - (3600 * 24)  # 24 hours ago

# Fetch historical candles with throttling handled automatically
historical_candles = await candles_feed.fetch_candles(
    start_time=start_time,
    end_time=end_time
)

print(f"Fetched {len(historical_candles)} historical candles")
```
