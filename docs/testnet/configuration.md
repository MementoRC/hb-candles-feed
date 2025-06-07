# Testnet Configuration

This guide explains how to configure the candles-feed package to use exchange testnets.

## Network Configuration

The testnet support is built around the `NetworkConfig` class, which allows configuring different network environments for different endpoint types.

## Basic Usage

To use testnet for all endpoints, create a testnet network configuration:

```python
from candles_feed import CandlesFeed
from candles_feed.core.network_config import NetworkConfig

# Create a feed using Binance testnet
feed = CandlesFeed(
    exchange="binance_spot",
    trading_pair="BTC-USDT",
    interval="1m",
    network_config=NetworkConfig.testnet()
)

# The rest of your code remains the same
await feed.start()
candles = feed.get_candles()
```

## Advanced Configuration

For more advanced use cases, you can create a hybrid configuration that uses different environments for different endpoint types:

```python
from candles_feed import CandlesFeed
from candles_feed.core.network_config import NetworkConfig, NetworkEnvironment, EndpointType

# Create a hybrid configuration
config = NetworkConfig.hybrid(
    candles=NetworkEnvironment.PRODUCTION,  # Use production for market data
    orders=NetworkEnvironment.TESTNET,      # Use testnet for orders
    account=NetworkEnvironment.TESTNET      # Use testnet for account info
)

# Create a feed with this configuration
feed = CandlesFeed(
    exchange="binance_spot",
    trading_pair="BTC-USDT",
    interval="1m",
    network_config=config
)
```

## Configuration API

The `NetworkConfig` class provides several factory methods for common configurations:

### Production Configuration

```python
# Create a configuration that uses production for all endpoints
config = NetworkConfig.production()
```

### Testnet Configuration

```python
# Create a configuration that uses testnet for all endpoints
config = NetworkConfig.testnet()
```

### Hybrid Configuration

```python
# Create a configuration with specific overrides
config = NetworkConfig.hybrid(
    candles=NetworkEnvironment.PRODUCTION,
    orders=NetworkEnvironment.TESTNET
)
```

### Manual Configuration

You can also create a configuration manually:

```python
from candles_feed.core.network_config import NetworkConfig, NetworkEnvironment, EndpointType

# Create a configuration with a default environment and specific overrides
config = NetworkConfig(
    default_environment=NetworkEnvironment.PRODUCTION,
    endpoint_overrides={
        EndpointType.ORDERS: NetworkEnvironment.TESTNET,
        EndpointType.ACCOUNT: NetworkEnvironment.TESTNET
    }
)
```

## Exchange-Specific Configuration

Some exchanges may require additional configuration for testnet usage:

### Binance

Binance requires separate API keys for testnet. You can obtain testnet API keys from [Binance Testnet](https://testnet.binance.vision/).

```python
from candles_feed import CandlesFeed
from candles_feed.core.network_config import NetworkConfig

# Create a feed with Binance testnet and API keys
feed = CandlesFeed(
    exchange="binance_spot",
    trading_pair="BTC-USDT",
    interval="1m",
    network_config=NetworkConfig.testnet(),
    api_key="your_testnet_api_key",
    api_secret="your_testnet_api_secret"
)
```

## Checking Configuration

You can check the current configuration using the `is_testnet_for` method:

```python
# Check if testnet is used for a specific endpoint type
is_testnet_for_orders = config.is_testnet_for(EndpointType.ORDERS)
```
