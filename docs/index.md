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

## Getting Started

To get started with the Candles Feed framework, check out the [Installation](getting_started/installation.md) and [Quick Start](getting_started/quick_start.md) guides.

For comprehensive examples of how to use the framework, see our [Examples](examples/simple_usage.md).

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