# Mocking Resources API Reference

This page documents the mocking infrastructure for testing exchange adapters and candles feed functionality.

## Mock Adapters

The framework provides several mock adapter implementations for testing purposes.

### Async Mock Adapter

::: candles_feed.mocking_resources.adapter.async_mocked_adapter.AsyncMockedAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

### Sync Mock Adapter

::: candles_feed.mocking_resources.adapter.sync_mocked_adapter.SyncMockedAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

### Hybrid Mock Adapter

::: candles_feed.mocking_resources.adapter.hybrid_mocked_adapter.HybridMockedAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

## Core Components

### Mock Exchange Server

::: candles_feed.mocking_resources.core.server.MockedExchangeServer
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

## Usage Examples

### Basic Mock Adapter Usage

```python
from candles_feed.mocking_resources.adapter import AsyncMockedAdapter
from candles_feed.core import NetworkClient, NetworkConfig

# Create mock adapter
config = NetworkConfig()
network_client = NetworkClient(config)

adapter = AsyncMockedAdapter(
    network_client=network_client,
    network_config=config,
    exchange_name="binance",
    trading_pair="BTCUSDT"
)

# Generate mock candle data
candles = await adapter.fetch_rest_candles("BTCUSDT", "1m", limit=100)
```

### Mock Server Setup

```python
from candles_feed.mocking_resources.core.server import MockedExchangeServer

# Create and start mock server
server = MockedExchangeServer(port=8080)
await server.start()

# Server will provide mock responses for testing
# Use normal adapters against this server
```

### Integration with Testing

```python
import pytest
from candles_feed.mocking_resources.adapter import AsyncMockedAdapter
from candles_feed.core import NetworkClient, NetworkConfig

@pytest.fixture
async def mock_adapter():
    config = NetworkConfig()
    network_client = NetworkClient(config)

    adapter = AsyncMockedAdapter(
        network_client=network_client,
        network_config=config,
        exchange_name="binance",
        trading_pair="BTCUSDT"
    )
    return adapter

@pytest.mark.asyncio
async def test_candles_retrieval(mock_adapter):
    """Test basic candle retrieval with mock adapter."""
    candles = await mock_adapter.fetch_rest_candles("BTCUSDT", "1m", limit=10)

    assert len(candles) == 10
    assert all(candle.trading_pair == "BTCUSDT" for candle in candles)
    assert all(candle.interval == "1m" for candle in candles)
```

### Error Simulation

```python
# Mock adapters can simulate various error conditions
from candles_feed.mocking_resources.adapter import AsyncMockedAdapter

# Configure adapter to simulate errors
adapter = AsyncMockedAdapter(
    network_client=network_client,
    network_config=config,
    exchange_name="binance",
    trading_pair="BTCUSDT",
    # Configure error simulation parameters if supported
)

# Test error handling
try:
    candles = await adapter.fetch_rest_candles("BTCUSDT", "1m")
except Exception as e:
    print(f"Handled error: {e}")
```

## Framework Design

The mocking infrastructure provides:

- **Mock Adapters**: Simulate exchange behavior without real API calls
- **Mock Server**: HTTP/WebSocket server that mimics exchange APIs
- **Test Integration**: Easy integration with pytest and asyncio testing
- **Error Simulation**: Test error handling and edge cases
- **Consistent Interface**: Mock components implement the same interfaces as production counterparts

This ensures tests accurately reflect real usage patterns while providing reliable, fast test execution without external dependencies.
