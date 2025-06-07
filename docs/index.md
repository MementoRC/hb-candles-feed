# Candles Feed Framework

Welcome to the Candles Feed documentation! This framework provides a modular, plugin-based approach to fetching and managing candlestick data from various cryptocurrency exchanges.

## Key Features

- **Pluggable Architecture**: Add support for new exchanges without modifying core code
- **Multiple Network Strategies**: Support for both WebSocket and REST API-based data collection
- **Robust Data Handling**: Data validation, sanitization, and standardization
- **Type Safety**: Strong typing throughout the codebase with Python 3.12 features
- **Easy to Extend**: Clear interfaces and separation of concerns
- **Performance Optimized**: Memory-efficient data structures and processing
- **Modern Python**: Leverages latest Python features and best practices
- **Comprehensive Testing Resources**: Mock servers and simulation tools for development and testing

## Framework Overview

```mermaid
graph LR
    Client[Client Application] --> CandlesFeed
    CandlesFeed --> ExchangeAdapter

    subgraph "Core Components"
        CandlesFeed
        NetworkStrategy
        DataProcessor
        ExchangeRegistry
    end

    subgraph "Exchange Adapters"
        ExchangeAdapter
        BinanceAdapter
        CoinbaseAdapter
        KrakenAdapter
        KuCoinAdapter
        OKXAdapter
        BybitAdapter
        NewExchangeAdapter[New Exchange...]
    end

    ExchangeRegistry --> ExchangeAdapter
    CandlesFeed --> NetworkStrategy
    CandlesFeed --> DataProcessor

    class NewExchangeAdapter fill:#f96;
```

## Supported Exchanges

- Binance (Spot and Perpetual)
- Bybit (Spot and Perpetual)
- Coinbase Advanced Trade
- Kraken Spot
- KuCoin (Spot and Perpetual)
- OKX (Spot and Perpetual)
- Gate.io (Spot and Perpetual)
- Hyperliquid (Perpetual)
- MEXC (Spot and Perpetual)
- AscendEX (Spot)

## Documentation Sections

This documentation is organized into the following sections:

### Getting Started
- [Installation](getting_started/installation.md): How to install and set up the framework
- [Quick Start](getting_started/quick_start.md): Simple examples to get you started
- [Architecture](getting_started/architecture.md): Understanding the framework design
- [Hummingbot Integration](getting_started/hummingbot_integration.md): Using with Hummingbot
- [Compatibility](getting_started/compatibility.md): Compatibility with original implementation

### Adapters
- [Overview](adapters/overview.md): Introduction to exchange adapters
- [Implementation](adapters/implementation.md): How to implement a new adapter
- [REST API](adapters/rest_api.md): Working with REST endpoints
- [WebSocket](adapters/websocket.md): Real-time data with WebSockets
- [Testing](adapters/testing.md): Testing your adapter implementation

### Testing Resources
- [Overview](testing_resources/overview.md): Introduction to testing tools
- [Mock Server](testing_resources/mock_server.md): Simulate exchange APIs

### Examples
- [Simple Usage](examples/simple_usage.md): Basic usage patterns
- [Binance Spot Example](examples/binance_spot_example.md): Working with Binance
- [Mock Server Example](examples/mock_server_example.md): Using testing resources

### API Reference
- [Core Components](api_reference/core.md): Reference for core framework classes

### Development
- [Coding Standards](development/coding_standards.md): Code style guidelines

## For Developers

If you want to contribute to the framework or add support for a new exchange, see the [Adding New Exchange](adapters/overview.md) section.

## Compatibility Notes

This package supports Python 3.12+ and leverages modern Python features such as:
- Type Protocol definitions
- Advanced data validation
- Concurrency with asyncio
- Type hints throughout the codebase

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
