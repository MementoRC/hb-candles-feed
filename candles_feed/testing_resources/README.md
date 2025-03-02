# Mock Exchange Testing Framework

This framework provides a modular and extensible way to simulate cryptocurrency exchange APIs for testing the candles feed package. It allows you to mock both REST and WebSocket endpoints with realistic data and behavior, making it ideal for integration and end-to-end testing without connecting to real exchanges.

## Key Features

- **Modular Design**: Core server functionality with exchange-specific plugins
- **Realistic Data**: Generates realistic candle data with price trends and volatility
- **Complete API Simulation**: Supports both REST and WebSocket endpoints
- **Network Simulation**: Can simulate latency, packet loss, and error responses
- **Rate Limiting**: Configurable rate limits for REST and WebSocket APIs
- **Multiple Exchanges**: Supports multiple exchange types through plugins

## Architecture

The framework consists of:

1. **Core Components**:
   - `MockExchangeServer`: The main server that handles requests
   - `MockCandleData`: Data model for candle information
   - `ExchangePlugin`: Abstract base class for exchange-specific plugins
   - `ExchangeType`: Enum of supported exchanges

2. **Exchange Plugins**:
   - Implement the `ExchangePlugin` interface for each exchange
   - Handle exchange-specific request/response formats
   - Define routes and handlers for the exchange's API

3. **Factory**:
   - `create_mock_server`: Factory function to create and configure a server

## Usage

### Basic Usage

```python
import asyncio
from candles_feed.testing_resources.mocks import ExchangeType, create_mock_server

async def main():
    # Create a mock Binance Spot server
    server = create_mock_server(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host='127.0.0.1',
        port=8080
    )
    
    # Start the server
    url = await server.start()
    print(f"Server started at {url}")
    
    # Wait for some time (or until interrupted)
    try:
        await asyncio.sleep(60)  # Run for 60 seconds
    finally:
        # Stop the server
        await server.stop()
        print("Server stopped")

asyncio.run(main())
```

### Advanced Configuration

```python
# Create a server with specific trading pairs
server = create_mock_server(
    exchange_type=ExchangeType.BINANCE_SPOT,
    trading_pairs=[
        ("BTCUSDT", "1m", 50000.0),  # Symbol, interval, initial price
        ("ETHUSDT", "5m", 3000.0),
        ("SOLUSDT", "15m", 100.0)
    ]
)

# Configure network conditions
server.set_network_conditions(
    latency_ms=50,           # 50ms latency
    packet_loss_rate=0.01,   # 1% packet loss
    error_rate=0.005         # 0.5% error rate
)

# Configure rate limits
server.set_rate_limits(
    rest_limit=1200,         # 1200 REST requests per minute
    rest_period_ms=60000,    # 1 minute period
    ws_limit=10,             # 10 WebSocket messages per second
    ws_burst=50              # 50 message burst allowed
)
```

## Creating a New Exchange Plugin

To add support for a new exchange:

1. Create a new module in `exchanges/` (e.g., `exchanges/new_exchange/`)
2. Create a plugin class that inherits from `ExchangePlugin`
3. Implement all required methods to handle the exchange's API format

Example:

```python
from candles_feed.testing_resources.mocks.core.exchange_plugin import ExchangePlugin
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType

class NewExchangePlugin(ExchangePlugin):
    def __init__(self, exchange_type: ExchangeType):
        super().__init__(exchange_type)
    
    @property
    def rest_routes(self):
        return {
            '/api/candles': ('GET', 'handle_klines'),
            # ... other routes
        }
    
    @property
    def ws_routes(self):
        return {
            '/ws': 'handle_websocket'
        }
    
    # Implement all other required methods
    # ...
```

## Testing with the Framework

### Unit Tests

```python
import asyncio
import unittest
from candles_feed.testing_resources.mocks import ExchangeType, create_mock_server

class TestCandlesFeed(unittest.TestCase):
    async def asyncSetUp(self):
        # Create and start a mock server for testing
        self.server = create_mock_server(ExchangeType.BINANCE_SPOT)
        self.server_url = await self.server.start()
        
        # Initialize your candles feed with the mock server URL
        self.candles_feed = YourCandlesFeed(base_url=self.server_url)
        await self.candles_feed.start()
    
    async def asyncTearDown(self):
        # Clean up
        await self.candles_feed.stop()
        await self.server.stop()
    
    async def test_get_candles(self):
        # Test getting candles from the mock server
        candles = await self.candles_feed.get_candles("BTCUSDT", "1m")
        self.assertIsNotNone(candles)
        self.assertGreater(len(candles), 0)
    
    # Helper to run async tests
    def test_get_candles_sync(self):
        asyncio.run(self.test_get_candles())
```

### Integration Tests

```python
from candles_feed.adapters.binance_spot import BinanceSpotAdapter
from candles_feed.testing_resources.mocks import ExchangeType, create_mock_server

async def test_integration():
    # Start mock server
    server = create_mock_server(ExchangeType.BINANCE_SPOT)
    url = await server.start()
    
    try:
        # Create adapter with mock server URL
        adapter = BinanceSpotAdapter(
            trading_pair="BTCUSDT",
            interval="1m",
            base_url=url,  # Use mock server URL instead of real Binance
            ws_url=f"ws://{server.host}:{server.port}/ws"
        )
        
        # Test adapter functionality with mock server
        await adapter.start()
        candles = await adapter.fetch_candles()
        print(f"Fetched {len(candles)} candles")
        
        # Wait for real-time updates
        await asyncio.sleep(10)
        
        # Check that we're receiving updates
        candles_after = await adapter.fetch_candles()
        print(f"Now have {len(candles_after)} candles")
        
        await adapter.stop()
    finally:
        await server.stop()
```

## Supported Exchanges

Currently, the following exchanges are supported:

- Binance Spot

More exchange plugins will be added in the future.

## Customization

You can customize various aspects of the mock server:

- **Candle Generation**: Modify volatility, trading patterns
- **Data Storage**: Add persistence for candle data
- **Error Scenarios**: Simulate specific error conditions
- **WebSocket Behavior**: Control connection drops, reconnects

## Contributing

To contribute a new exchange plugin:

1. Create a new directory under `exchanges/` for your exchange
2. Implement the `ExchangePlugin` interface in a new class
3. Register your plugin in the plugin registry
4. Add tests to verify your implementation
5. Update documentation with the new supported exchange