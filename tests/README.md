# Candles Feed Testing Suite

This directory contains tests for the `candles_feed` package. The tests are organized into three main categories:

## Test Structure

### Unit Tests (`unit/`)
Unit tests verify individual components in isolation. These tests mock external dependencies and focus on testing specific functionality.

#### Core Component Tests
- `test_candle_data.py`: Tests for the `CandleData` class
- `test_candles_feed.py`: Tests for the `CandlesFeed` class
- `test_data_processor.py`: Tests for the `DataProcessor` class
- `test_exchange_registry.py`: Tests for the `ExchangeRegistry` class
- `test_network_client.py`: Tests for the `NetworkClient` class
- `test_network_strategies.py`: Tests for the network strategies

#### Adapter Tests
Tests for each exchange adapter are in their respective directories:
- `adapters/binance_spot/test_binance_spot_adapter.py`
- `adapters/bybit_spot/test_bybit_spot_adapter.py`
- `adapters/coinbase_advanced_trade/test_coinbase_advanced_trade_adapter.py`
- `adapters/kraken_spot/test_kraken_spot_adapter.py`
- `adapters/kucoin_spot/test_kucoin_spot_adapter.py`
- `adapters/okx_spot/test_okx_spot_adapter.py`

### Integration Tests (`integration/`)
Integration tests verify that components work correctly together.

- `test_candles_feed_integration.py`: Tests the interaction between `CandlesFeed` and various adapters
- `test_mock_server.py`: Tests for the mock server used in end-to-end tests

### End-to-End Tests (`e2e/`)
End-to-end tests verify the system as a whole.

- `test_candles_feed_e2e.py`: Tests the entire system using a mock exchange server
- `improved_e2e_test.py`: Enhanced end-to-end tests with better error handling and network simulation

### Enhanced Testing Resources

The package now includes an improved mock server architecture in `candles_feed/testing_resources/mocks/`:

- **Core Components**:
  - `exchange_plugin.py`: Base class for exchange-specific plugins
  - `exchange_type.py`: Enumeration of supported exchange types
  - `server.py`: Enhanced mock server implementation
  - `candle_data.py`: Mock candle data implementation

- **Exchange Plugins**:
  - `exchanges/binance_spot/plugin.py`: Binance Spot plugin implementation
  - (additional plugins for other exchanges can be added here)

These resources provide more realistic testing with features like network simulation, rate limiting, and exchange-specific behavior.

## Running the Tests

To run the tests, use pytest:

```bash
# Run all tests
pytest -xvs

# Run specific test category
pytest -xvs tests/unit/
pytest -xvs tests/integration/
pytest -xvs tests/e2e/
pytest -xvs tests/test_end_to_end.py

# Run specific test file
pytest -xvs tests/unit/core/test_candle_data.py

# Run with coverage
pytest --cov=candles_feed
```

## Test Fixtures

Common test fixtures are defined in `conftest.py`. These fixtures provide mock objects and data for tests.

## Adding New Tests

When adding new adapters or features, please follow the existing test patterns:

1. Create unit tests for each new component
2. Add integration tests for interactions with other components
3. Update end-to-end tests if needed
4. Consider creating a plugin for the enhanced mock server 
5. Update fixtures in `conftest.py` if needed
6. Add error handling tests using network simulation

## Testing Strategies

The testing suite uses several strategies:

- **Mocking**: External dependencies are mocked using `unittest.mock` and pytest fixtures
- **Parametrized Tests**: Tests that run with multiple inputs
- **Async Testing**: Using pytest-asyncio for testing async code
- **Mock Server**: Using a custom mock server for end-to-end testing
- **Network Simulation**: Testing with simulated network conditions (latency, errors, packet loss)
- **Plugin Architecture**: Using plugins to customize mock server behavior for different exchanges

## Recent Improvements

We've made several enhancements to the testing infrastructure:

1. **Better URL Patching**: More consistent handling of REST and WebSocket URL patching
2. **Error Handling Tests**: Tests for handling network errors and invalid inputs
3. **Resource Cleanup**: Improved cleanup of resources in tests
4. **Enhanced Mock Server**: Plugin-based architecture for more realistic exchange simulation

For more details on these improvements, see `testing_improvements.md`.