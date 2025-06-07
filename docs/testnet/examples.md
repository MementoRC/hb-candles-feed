# Usage Examples

This page provides practical examples of using testnet support in the candles-feed package.

## Basic Testnet Example

This example demonstrates basic usage of testnet mode:

```python
import asyncio
from candles_feed import CandlesFeed
from candles_feed.core.network_config import NetworkConfig

async def main():
    # Create a feed with testnet configuration
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        network_config=NetworkConfig.testnet()
    )

    try:
        # Start the feed
        print("Starting feed with testnet configuration...")
        await feed.start()

        # Wait for some data to arrive
        print("Waiting for initial data...")
        await asyncio.sleep(5)

        # Get and print candles
        candles = feed.get_candles()
        print(f"Received {len(candles)} candles from testnet")

        # Print the most recent candle
        if candles:
            latest = candles[-1]
            print(f"Latest candle: timestamp={latest.timestamp}, "
                  f"open={latest.open}, high={latest.high}, "
                  f"low={latest.low}, close={latest.close}, "
                  f"volume={latest.volume}")

    finally:
        # Stop the feed
        print("Stopping feed...")
        await feed.stop()

# Run the example
asyncio.run(main())
```

## Hybrid Configuration Example

This example demonstrates using a hybrid configuration that uses testnet for orders but production for market data:

```python
import asyncio
from candles_feed import CandlesFeed
from candles_feed.core.network_config import NetworkConfig, NetworkEnvironment, EndpointType

async def main():
    # Create a hybrid config that uses testnet for orders but production for candles
    config = NetworkConfig.hybrid(
        candles=NetworkEnvironment.PRODUCTION,
        orders=NetworkEnvironment.TESTNET
    )

    # Create a feed with this configuration
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        network_config=config
    )

    try:
        # Start the feed
        print("Starting feed with hybrid configuration...")
        await feed.start()

        # Wait for some data to arrive
        print("Waiting for initial data...")
        await asyncio.sleep(5)

        # Get and print candles
        candles = feed.get_candles()
        print(f"Received {len(candles)} candles from production")

        # In a real implementation, we would now place orders on testnet
        # while using production market data
        print("In a real implementation, orders would go to testnet "
              "while using production market data")

    finally:
        # Stop the feed
        print("Stopping feed...")
        await feed.stop()

# Run the example
asyncio.run(main())
```

## Multiple Exchange Example

This example demonstrates using testnet with multiple exchanges:

```python
import asyncio
from candles_feed import CandlesFeed
from candles_feed.core.network_config import NetworkConfig

async def main():
    # Create feeds for different exchanges with testnet
    binance_feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        network_config=NetworkConfig.testnet()
    )

    # Note: This is a placeholder - implementation would depend on
    # which exchanges have testnet support
    other_exchange_feed = CandlesFeed(
        exchange="other_exchange",
        trading_pair="BTC-USDT",
        interval="1m",
        network_config=NetworkConfig.testnet()
    )

    try:
        # Start both feeds
        print("Starting feeds with testnet configuration...")
        await asyncio.gather(
            binance_feed.start(),
            other_exchange_feed.start()
        )

        # Wait for some data to arrive
        print("Waiting for initial data...")
        await asyncio.sleep(5)

        # Get and print candles from both feeds
        binance_candles = binance_feed.get_candles()
        other_exchange_candles = other_exchange_feed.get_candles()

        print(f"Received {len(binance_candles)} candles from Binance testnet")
        print(f"Received {len(other_exchange_candles)} candles from other exchange testnet")

    finally:
        # Stop both feeds
        print("Stopping feeds...")
        await asyncio.gather(
            binance_feed.stop(),
            other_exchange_feed.stop()
        )

# Run the example
asyncio.run(main())
```

## Advanced Configuration Example

This example demonstrates creating a custom network configuration:

```python
import asyncio
from candles_feed import CandlesFeed
from candles_feed.core.network_config import NetworkConfig, NetworkEnvironment, EndpointType

# Create a custom configuration
custom_config = NetworkConfig(
    default_environment=NetworkEnvironment.PRODUCTION,
    endpoint_overrides={
        EndpointType.CANDLES: NetworkEnvironment.PRODUCTION,
        EndpointType.TICKER: NetworkEnvironment.PRODUCTION,
        EndpointType.TRADES: NetworkEnvironment.PRODUCTION,
        EndpointType.ORDERS: NetworkEnvironment.TESTNET,
        EndpointType.ACCOUNT: NetworkEnvironment.TESTNET
    }
)

# Create a feed with this configuration
feed = CandlesFeed(
    exchange="binance_spot",
    trading_pair="BTC-USDT",
    interval="1m",
    network_config=custom_config
)
```
