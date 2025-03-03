# Candles Feed

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A high-performance, modular library for fetching and working with cryptocurrency candlestick data from various exchanges.

## Features

- 📊 **Cross-Exchange Compatibility**: Connect to multiple exchanges with a consistent interface
- 📈 **Real-time Data**: Stream candlestick data in real-time using WebSockets
- 🕰️ **Historical Data**: Fetch historical candlestick data via REST APIs
- 🔌 **Pluggable Design**: Add new exchanges through the adapter system
- 🧰 **Flexible Processing**: Work with data in different formats (pandas, arrays, objects)
- 📏 **Type-Safe**: Modern Python 3.12+ with complete type annotations
- 🛡️ **Robust**: Resilient to network issues and exchange quirks

## Supported Exchanges

- Binance (Spot and Perpetual)
- Bybit (Spot and Perpetual)
- Coinbase Advanced Trade
- KuCoin (Spot and Perpetual)
- Kraken Spot
- OKX (Spot and Perpetual)
- Gate.io (Spot and Perpetual)
- Hyperliquid (Perpetual)
- MEXC (Spot and Perpetual)
- AscendEX (Spot)

## Installation

```bash
# Option 1: Install directly
pip install hb-candles-feed

# Option 2: Install with development dependencies
pip install -e ".[dev]"

# Option 3: Use conda setup (recommended)
./setup-dev-env.sh
```

## Quick Start

```python
import asyncio
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.exchange_registry import ExchangeRegistry

async def main():
    # Discover available adapters
    ExchangeRegistry.discover_adapters()
    
    # Create a feed for Binance BTC-USDT
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1h",
        max_records=24  # Keep last 24 hours
    )
    
    # Fetch historical candles
    candles = await feed.fetch_candles()
    print(f"Fetched {len(candles)} candles")
    
    # Get as pandas DataFrame
    df = feed.get_candles_df()
    print(df.head())
    
    # Clean up resources
    await feed.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## WebSocket Streaming

```python
import asyncio
from candles_feed.core.candles_feed import CandlesFeed

async def main():
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m"
    )
    
    # Start WebSocket streaming
    await feed.start(strategy="websocket")
    print("WebSocket feed started")
    
    # Monitor for updates
    for _ in range(60):
        await asyncio.sleep(1)
        candles = feed.get_candles()
        if candles:
            latest = candles[-1]
            print(f"Latest price: {latest.close}")
    
    # Stop the feed
    await feed.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Architecture Overview

The Candles Feed package has a modular architecture:

```
candles_feed/
├── core/                    # Core functionality
│   ├── candles_feed.py      # Main entry point
│   ├── candle_data.py       # Data structure
│   ├── data_processor.py    # Data sanitization
│   ├── exchange_registry.py # Adapter registry
│   ├── network_client.py    # Network handling
│   ├── network_strategies.py # Connection strategies
│   └── protocols.py         # Interface definitions
│
├── adapters/                # Exchange adapters
│   ├── base_adapter.py      # Base adapter class
│   ├── binance_spot/        # Binance implementation
│   ├── coinbase_advanced_trade/ # Coinbase implementation
│   └── ... (other exchanges)
│
└── utils/                   # Utility functions
    └── time_utils.py        # Time conversion helpers
```

## Building with Cython (Optional)

For performance-critical code, Cython compilation is supported:

```bash
# Force recompilation of Cython modules
python cmake/cython_builder.py candles_feed
```

## Running the Tests

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/e2e/

# Run with coverage
python -m pytest --cov=candles_feed
```

## Documentation

For complete documentation, see the `docs/` directory, which includes:

- [Installation Guide](docs/getting_started/installation.md)
- [Quick Start Guide](docs/getting_started/quick_start.md)
- [Example Usage](docs/examples/simple_usage.md)
- [Adapter Implementation Guide](docs/adapters/implementation.md)

## Requirements

- Python 3.12+
- aiohttp
- pandas
- numpy

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.