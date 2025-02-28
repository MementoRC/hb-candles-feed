# Testing Strategy for Candles Feed

This document outlines the testing strategy for the Candles Feed package.

## Overview

The Candles Feed package has a comprehensive testing suite that follows a pyramid approach:

1. **Unit Tests**: Testing individual components in isolation
2. **Integration Tests**: Testing interactions between components
3. **End-to-End Tests**: Testing the entire system with a mock exchange server

## Test Categories

### Unit Tests

Unit tests verify that individual components work correctly in isolation. They mock external dependencies and focus on specific functionality.

**Core Components:**
- CandleData: Data representation for candlestick data
- CandlesFeed: Main class for managing candle data
- DataProcessor: Processing and validating candle data
- ExchangeRegistry: Registry for exchange adapters
- NetworkClient: Network operations (REST and WebSocket)
- NetworkStrategies: Strategies for fetching data (REST polling, WebSocket)

**Exchange Adapters:**
- BinanceSpotAdapter
- BybitSpotAdapter
- CoinbaseAdvancedTradeAdapter
- KrakenSpotAdapter
- KuCoinSpotAdapter
- OKXSpotAdapter

### Integration Tests

Integration tests verify that components work correctly together. These tests use mocked external services but test real interactions between components.

**Key Integration Scenarios:**
- CandlesFeed with various adapters
- Network client with network strategies
- Data processor with candle storage

### End-to-End Tests

End-to-end tests verify the entire system works correctly. They use a mock exchange server to simulate real API interactions.

**Key E2E Scenarios:**
- Fetching historical candles via REST
- Streaming candles via WebSocket
- Multiple feeds running concurrently
- Handling network errors and reconnections

## Testing Infrastructure

### Fixtures

Common test fixtures are defined in `conftest.py`. These fixtures provide:
- Mock adapters
- Mock network clients
- Sample candle data
- Mock API responses
- Test utilities

### Mock Exchange Server

A mock exchange server (`mock_exchange_server.py`) simulates real exchange APIs for end-to-end testing. It provides:
- REST endpoints for candle data
- WebSocket endpoints for streaming updates
- Realistic data generation
- Configurable behavior

### Test Markers

Tests are marked with pytest markers to categorize them:
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests

## Running Tests

Tests can be run using the provided `run_tests.py` script or directly with pytest:

```bash
# Using the test runner
./run_tests.py --unit
./run_tests.py --integration
./run_tests.py --e2e
./run_tests.py --all
./run_tests.py --cov  # Generate coverage report

# Using pytest directly
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
pytest --cov=candles_feed
```

## Coverage Goals

The test suite aims for high code coverage:
- Core components: >95% line coverage
- Adapter implementations: >90% line coverage
- Overall package: >90% line coverage

## Continuous Integration

The test suite is designed to run in CI environments:
- Fast unit tests run on every pull request
- Integration tests run on every pull request
- End-to-end tests run on every pull request and main branch commits
- Coverage reports are generated and tracked