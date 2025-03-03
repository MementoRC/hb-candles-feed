# Exchange Simulation Testing Framework

This framework provides a sophisticated exchange simulation system for testing cryptocurrency trading applications, specifically designed for the candles feed package. It enables high-fidelity simulation of exchange APIs, including REST endpoints and WebSocket connections, with realistic data generation and error simulation capabilities.

## Key Features

- **Full Exchange Simulation**: Complete REST and WebSocket API simulation
- **Realistic Market Data**: Generates candle data with configurable price dynamics
- **Network Condition Simulation**: Simulate latency, packet loss, and errors
- **Rate Limiting**: Configurable rate limits matching real exchanges
- **Extensible Plugin System**: Add support for any exchange with plugins
- **Testing Utilities**: Ready for integration, unit, and E2E tests

## Architecture

The framework consists of:

1. **Core Server**:
   - `MockExchangeServer`: HTTP/WS server with complete exchange behavior
   - `ExchangePlugin`: Plugin system for exchange-specific behavior
   - `CandleDataFactory`: Realistic market data generation

2. **Exchange Plugins**:
   - Exchange-specific request/response formats
   - REST and WebSocket endpoint implementations
   - Data conversion utilities

3. **Testing Utilities**:
   - Test fixtures for pytest
   - Helper functions for test setup/teardown
   - Factory functions for common test scenarios

## Usage in Integration Tests

```python
import pytest
from candles_feed.core.candles_feed import CandlesFeed

class TestCandlesFeedIntegration:
    @pytest.fixture
    async def mock_server(self):
        """Create a standalone mock server for testing."""
        # Create mock server here
        # ...

    @pytest.mark.asyncio
    async def test_rest_strategy_integration(self, mock_server):
        """Test CandlesFeed with REST polling strategy."""
        mock_server_url = mock_server.url
        
        # Create feed for testing
        feed = CandlesFeed(
            exchange="binance_spot",
            trading_pair="BTC-USDT",
            interval="1m",
            max_records=100
        )
        
        # Override adapter REST URL
        feed._adapter.get_rest_url = lambda: f"{mock_server_url}/api/v3/klines"
        
        try:
            # Start the feed with REST polling strategy
            await feed.start(strategy="polling")
            
            # Verify candles were retrieved
            candles = feed.get_candles()
            assert len(candles) > 0
        
        finally:
            # Stop the feed
            await feed.stop()
```

## Adding a New Exchange

To add support for a new exchange, create a plugin that implements the exchange's API:

```python
from candles_feed.testing_resources.exchange_simulation.core.exchange_plugin import ExchangePlugin
from candles_feed.testing_resources.exchange_simulation.core.exchange_type import ExchangeType

class NewExchangePlugin(ExchangePlugin):
    def __init__(self, exchange_type: ExchangeType):
        super().__init__(exchange_type)
    
    @property
    def rest_routes(self):
        return {
            '/api/candles': ('GET', 'handle_klines'),
            # ... other routes
        }
    
    # Implement required methods
    # ...
```

## Advanced Configuration

The framework provides advanced configuration options for different testing scenarios:

```python
# Configure network conditions for error testing
server.set_network_conditions(
    latency_ms=50,          # 50ms latency
    packet_loss_rate=0.2,   # 20% packet loss
    error_rate=0.1          # 10% error responses
)

# Set different rate limits
server.set_rate_limits(
    rest_limit=120,         # 120 requests per minute
    rest_period_ms=60000,   # 1 minute period
    ws_limit=5,             # 5 messages per second
    ws_burst=10             # 10 messages burst
)
```

## Testing Error Handling

The framework excels at testing error handling and recovery:

```python
# Test error handling
async def test_error_handling(mock_server):
    # Set error conditions
    mock_server.set_network_conditions(
        latency_ms=100,
        packet_loss_rate=0.2,
        error_rate=0.2
    )
    
    # Create feed and test with error conditions
    # ...
    
    # Reset conditions for recovery testing
    mock_server.set_network_conditions(
        latency_ms=0,
        packet_loss_rate=0.0,
        error_rate=0.0
    )
    
    # Verify recovery
    # ...
```

## Currently Supported Exchanges

- Binance Spot
- More exchanges coming soon

## For External Projects

This framework is designed to be used by external projects that need to test their integration with cryptocurrency exchanges. You can:

1. Import the simulation framework in your test code
2. Create mock servers for supported exchanges
3. Point your code to the mock server instead of real exchanges
4. Test all scenarios including error handling
5. Extend with plugins for exchanges not yet supported