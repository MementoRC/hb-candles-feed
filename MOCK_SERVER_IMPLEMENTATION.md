# Mock Exchange Server Implementation Guide

This document outlines the design and implementation plan for a modular mock exchange server to be used for testing the candles feed package in larger projects.

## Overview

A modular mock exchange server is needed to simulate various cryptocurrency exchange APIs (both REST and WebSocket) for testing without connecting to real exchanges. This implementation will allow for:

1. Realistic candle data generation
2. Simulation of network conditions (latency, packet loss, errors)
3. Exchange-specific API behaviors
4. Testing in isolation from real exchanges

## Proposed Directory Structure

```
candles_feed/
├── testing_resources/            # New directory for testing resources
│   ├── __init__.py               # Package init with proper exports
│   ├── mocks/                    # Mock server implementation
│   │   ├── __init__.py           # Exports core components
│   │   ├── core/                 # Core mock server components
│   │   │   ├── __init__.py
│   │   │   ├── candle_data.py    # Mock candle data model
│   │   │   ├── exchange_plugin.py # Plugin interface
│   │   │   ├── exchange_type.py  # Exchange type enum
│   │   │   ├── factory.py        # Server factory
│   │   │   └── server.py         # Core server implementation
│   │   └── exchanges/            # Exchange-specific plugins
│   │       ├── __init__.py
│   │       ├── binance_spot/     # Binance Spot implementation
│   │       │   ├── __init__.py
│   │       │   └── plugin.py     # Binance plugin implementation
│   │       └── ... other exchanges
│   └── examples/                 # Example usage
│       ├── __init__.py
│       └── binance_spot_example.py
└── ... existing directories
```

## Implementation Components

1. **MockCandleData**: A data class for mock candle information with realistic generation capabilities
2. **ExchangePlugin**: Abstract base class defining the interface for exchange-specific plugins
3. **ExchangeType**: Enum of supported exchanges
4. **MockExchangeServer**: Core server that handles requests and delegates to plugins
5. **Exchange-specific plugins**: Implementations of ExchangePlugin for each exchange

## Key Features

1. **Modular Design**: Core server functionality with exchange-specific plugins
2. **Realistic Data**: Generates realistic candle data with price trends and volatility
3. **Complete API Simulation**: Supports both REST and WebSocket endpoints
4. **Network Simulation**: Can simulate latency, packet loss, and error responses
5. **Rate Limiting**: Configurable rate limits for REST and WebSocket APIs

## Integration with Testing Framework

The mock server is designed to be used in tests as follows:

```python
import pytest
from candles_feed.testing_resources.mocks import ExchangeType, create_mock_server

@pytest.fixture
async def binance_mock_server():
    """Create and start a Binance mock server for testing."""
    server = create_mock_server(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host='127.0.0.1',
        port=8080
    )
    
    # Add some trading pairs
    server.add_trading_pair("BTCUSDT", "1m", 50000.0)
    server.add_trading_pair("ETHUSDT", "1m", 3000.0)
    
    # Start the server
    url = await server.start()
    
    yield server
    
    # Clean up
    await server.stop()

async def test_candles_feed_with_mock_server(binance_mock_server):
    """Test CandlesFeed using a mock server."""
    # Initialize your candles feed with the mock server URL
    feed = CandlesFeed(
        trading_pair="BTCUSDT",
        interval="1m",
        exchange="binance",
        base_url=f"http://{binance_mock_server.host}:{binance_mock_server.port}"
    )
    
    await feed.start()
    # ... test assertions ...
    await feed.stop()
```

## Implementation Plan

1. Create core modules:
   - `candle_data.py` - Mock candle data class
   - `exchange_plugin.py` - Exchange plugin interface
   - `exchange_type.py` - Exchange type enum
   - `server.py` - Core server implementation
   - `factory.py` - Server factory

2. Create Binance implementation as a reference:
   - `exchanges/binance_spot/plugin.py`

3. Add comprehensive tests:
   - Unit tests for each component
   - Integration tests with CandlesFeed

4. Create additional exchange implementations:
   - Coinbase, Kraken, KuCoin, etc.

5. Add examples and documentation

## Conclusion

This implementation will provide a robust, modular framework for testing the candles feed package without relying on real exchanges. It will allow for comprehensive testing of all adapter implementations and ensure that the package works correctly under various network conditions.