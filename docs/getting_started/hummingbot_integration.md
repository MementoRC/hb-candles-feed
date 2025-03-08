# Integrating with Hummingbot

The Candles Feed framework can be used both as a standalone package and as an integrated component within Hummingbot. This guide explains how to use Candles Feed with Hummingbot's networking components.

## Overview

Candles Feed provides a seamless integration path with Hummingbot through adapter components that:

1. Use Hummingbot's network components when available
2. Fall back to standalone implementations when used independently
3. Maintain the same API and behavior in both scenarios

This integration approach allows you to:

- Reuse Hummingbot's throttling and rate limiting
- Share network connections with other Hummingbot components
- Maintain consistent API access patterns across Hummingbot

## Integration Components

The integration is implemented through several key components:

- **Adapter Layer**: Converts between Hummingbot and Candles Feed interfaces
- **Factory Pattern**: Selects the appropriate implementation based on available components
- **Protocol-based Design**: Uses Python's Protocol typing system for flexible implementations

## Using Candles Feed with Hummingbot

### Within a Hummingbot Strategy

To use Candles Feed within a Hummingbot strategy, use the `create_candles_feed_with_hummingbot` helper function:

```python
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.connections.connections_factory import ConnectionsFactory
from hummingbot.data_feed import create_candles_feed_with_hummingbot

class MyStrategy:
    def __init__(self, ...):
        # Set up Hummingbot's networking components
        self._throttler = AsyncThrottler(rate_limits=[...])
        self._connections_factory = ConnectionsFactory()
        self._web_assistants_factory = WebAssistantsFactory(
            throttler=self._throttler,
            connections_factory=self._connections_factory
        )
        
        # Create a CandlesFeed instance that uses Hummingbot's components
        self._candles_feed = create_candles_feed_with_hummingbot(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            throttler=self._throttler,
            web_assistants_factory=self._web_assistants_factory
        )
    
    async def start(self, ...):
        # Start the feed
        await self._candles_feed.start()
        
    async def stop(self, ...):
        # Stop the feed
        await self._candles_feed.stop()
        
    def process_candles(self):
        # Get candles as DataFrame
        df = self._candles_feed.get_candles_df()
        # Use the DataFrame for analysis, etc.
```

### Using CandlesFeed Directly

You can also use the `CandlesFeed` class directly with Hummingbot components, though the helper function is recommended:

```python
from candles_feed import CandlesFeed

# Create a CandlesFeed instance directly
candles_feed = CandlesFeed(
    exchange="binance_spot",
    trading_pair="BTC-USDT",
    interval="1m",
    hummingbot_components={
        "throttler": throttler,
        "web_assistants_factory": web_assistants_factory
    }
)
```

## Benefits of Integration

### Resource Sharing

By using Hummingbot's networking components, you can:

- Share rate limiting across multiple components
- Avoid duplicate connections to the same exchange
- Benefit from Hummingbot's connection management

### Consistent API Access

The integration ensures:

- The same rate limits are respected across all components
- Authentication is handled consistently
- Connection lifecycle is coordinated

### Seamless Fallback

If Hummingbot components are not available, Candles Feed will:

- Fall back to its own standalone implementations
- Maintain the same API and behavior
- Work with minimal dependencies

## Advanced Usage

### Custom Network Strategies

You can customize how candles are fetched by selecting a strategy:

```python
# Use WebSocket for real-time updates when supported
await candles_feed.start(strategy="websocket")

# Use REST polling for historical data
await candles_feed.start(strategy="polling")

# Let the system decide based on exchange capabilities
await candles_feed.start(strategy="auto")
```

### Handling Throttling

Hummingbot's throttler manages rate limits automatically:

```python
# The throttler will handle rate limiting
candles = await candles_feed.fetch_candles(
    start_time=start_timestamp,
    end_time=end_timestamp
)
```

## Testing with Mock Components

For testing without actual exchange connections, you can use the provided mocks:

```python
from mocking_resources.hummingbot import (
    create_mock_hummingbot_components
)

# Create mock components
mock_components = create_mock_hummingbot_components(
    rest_responses={
        "https://api.binance.com/api/v3/klines": [...],
    },
    ws_messages=[...]
)

# Create a CandlesFeed with mock components
candles_feed = create_candles_feed_with_hummingbot(
    exchange="binance_spot",
    trading_pair="BTC-USDT",
    throttler=mock_components["throttler"],
    web_assistants_factory=mock_components["web_assistants_factory"]
)
```

See the [examples](../examples/hummingbot_integration.md) for more detailed usage examples.