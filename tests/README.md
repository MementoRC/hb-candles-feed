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

### End-to-End Tests (`e2e/`)
End-to-end tests verify the system as a whole.

- `test_candles_feed_e2e.py`: Tests the entire system using a mock exchange server

### Mocks (`mocks/`)
Contains mock implementations for testing.

- `mock_exchange_server.py`: A mock exchange server for testing

## Running the Tests

To run the tests, use pytest:

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run specific test file
pytest tests/unit/core/test_candle_data.py

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
4. Update fixtures in `conftest.py` if needed

## Testing Strategies

The testing suite uses several strategies:

- **Mocking**: External dependencies are mocked using `unittest.mock` and pytest fixtures
- **Parametrized Tests**: Tests that run with multiple inputs
- **Async Testing**: Using pytest-asyncio for testing async code
- **Mock Server**: Using a custom mock server for end-to-end testing