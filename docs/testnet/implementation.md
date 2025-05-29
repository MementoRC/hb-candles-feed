# Implementation Guide

This guide explains how to implement testnet support for a new exchange adapter.

## Adding Testnet Support to an Adapter

To add testnet support to an exchange adapter, follow these steps:

### 1. Define Testnet URLs

First, add the testnet URLs to the exchange's constants file:

```python
# In adapters/your_exchange/constants.py

# Production URLs (existing)
REST_URL = "https://api.example.com/v1"
WSS_URL = "wss://ws.example.com"

# Testnet URLs (new)
TESTNET_REST_URL = "https://testnet.example.com/v1"
TESTNET_WSS_URL = "wss://testnet-ws.example.com"
```

### 2. Apply the TestnetSupportMixin

Apply the `TestnetSupportMixin` to your adapter class:

```python
# In adapters/your_exchange/adapter.py
from candles_feed.core.network_config import NetworkConfig
from candles_feed.adapters.adapter_mixins import TestnetSupportMixin

class YourExchangeAdapter(YourExchangeBaseAdapter, TestnetSupportMixin):
    """Your exchange adapter with testnet support."""
    
    def __init__(self, *args, network_config: Optional[NetworkConfig] = None, **kwargs):
        """Initialize the adapter.
        
        :param network_config: Network configuration for testnet/production
        :param args: Additional positional arguments
        :param kwargs: Additional keyword arguments
        """
        super().__init__(*args, network_config=network_config, **kwargs)
```

### 3. Implement Testnet URL Methods

Implement the required testnet URL methods:

```python
def _get_testnet_rest_url(self) -> str:
    """Get testnet REST URL for candles.
    
    :return: Testnet REST URL for candles endpoint
    """
    return f"{TESTNET_REST_URL}{CANDLES_ENDPOINT}"

def _get_testnet_ws_url(self) -> str:
    """Get testnet WebSocket URL.
    
    :return: Testnet WebSocket URL
    """
    return TESTNET_WSS_URL
```

## Testing Your Implementation

Create tests to verify your testnet implementation:

```python
def test_production_urls(self):
    """Test production URLs."""
    adapter = YourExchangeAdapter(network_config=NetworkConfig.production())
    assert adapter._get_rest_url() == f"{REST_URL}{CANDLES_ENDPOINT}"
    assert adapter._get_ws_url() == WSS_URL

def test_testnet_urls(self):
    """Test testnet URLs."""
    adapter = YourExchangeAdapter(network_config=NetworkConfig.testnet())
    assert adapter._get_rest_url() == f"{TESTNET_REST_URL}{CANDLES_ENDPOINT}"
    assert adapter._get_ws_url() == TESTNET_WSS_URL
```

## Integration Testing

Create integration tests to verify your adapter works with testnet:

```python
@pytest.mark.asyncio
async def test_your_exchange_testnet():
    """Test your exchange adapter with testnet."""
    feed = CandlesFeed(
        exchange="your_exchange",
        trading_pair="BTC-USDT",
        interval="1m",
        network_config=NetworkConfig.testnet()
    )
    
    try:
        await feed.start()
        await asyncio.sleep(5)  # Wait for data
        
        # Check that we got candles
        candles = feed.get_candles()
        assert len(candles) > 0
    finally:
        await feed.stop()
```

## Implementation Example: Binance

Here's an example implementation for Binance:

```python
# In adapters/binance/constants.py
SPOT_REST_URL = "https://api.binance.com"
SPOT_WSS_URL = "wss://stream.binance.com:9443/ws"
SPOT_CANDLES_ENDPOINT = "/api/v3/klines"

SPOT_TESTNET_REST_URL = "https://testnet.binance.vision"
SPOT_TESTNET_WSS_URL = "wss://testnet.binance.vision/ws"

# In adapters/binance/spot_adapter.py
class BinanceSpotAdapter(BinanceBaseAdapter, TestnetSupportMixin):
    """Binance spot adapter with testnet support."""
    
    def __init__(self, *args, network_config: Optional[NetworkConfig] = None, **kwargs):
        """Initialize the adapter.
        
        :param network_config: Network configuration for testnet/production
        :param args: Additional positional arguments
        :param kwargs: Additional keyword arguments
        """
        super().__init__(*args, network_config=network_config, **kwargs)
    
    def _get_testnet_rest_url(self) -> str:
        """Get Binance testnet REST URL for candles.
        
        :return: Testnet REST URL for candles endpoint
        """
        return f"{SPOT_TESTNET_REST_URL}{SPOT_CANDLES_ENDPOINT}"
    
    def _get_testnet_ws_url(self) -> str:
        """Get Binance testnet WebSocket URL.
        
        :return: Testnet WebSocket URL
        """
        return SPOT_TESTNET_WSS_URL
```