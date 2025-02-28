# Candles Feed Framework

Welcome to the Candles Feed documentation! This framework provides a modular, plugin-based approach to fetching and managing candlestick data from various cryptocurrency exchanges.

## Key Features

- **Pluggable Architecture**: Add support for new exchanges without modifying core code
- **Multiple Network Strategies**: Support for both WebSocket and REST API-based data collection
- **Robust Data Handling**: Data validation, sanitization, and standardization
- **Type Safety**: Strong typing throughout the codebase
- **Easy to Extend**: Clear interfaces and separation of concerns

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

- Binance Spot
- Bybit Spot
- Coinbase Advanced Trade
- Kraken Spot
- KuCoin Spot
- OKX Spot

## Getting Started

To get started with the Candles Feed framework, check out the [Installation](getting_started/installation.md) and [Quick Start](getting_started/quick_start.md) guides.

## For Developers

If you want to contribute to the framework or add support for a new exchange, see the [Adding New Exchange](adapters/overview.md) section.

## License

This project is licensed under the MIT License - see the LICENSE file for details.