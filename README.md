# Candles Feed

[![Candles Feed CI](https://github.com/MementoRC/hb-candles-feed/actions/workflows/ci.yml/badge.svg)](https://github.com/MementoRC/hb-candles-feed/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/MementoRC/hb-candles-feed/branch/main/graph/badge.svg)](https://codecov.io/gh/MementoRC/hb-candles-feed)
[![PyPI version](https://badge.fury.io/py/hummingbot-candles-feed.svg)](https://badge.fury.io/py/hummingbot-candles-feed)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A modular, plugin-based framework for fetching and managing candle data from cryptocurrency exchanges.

## Overview

The Candles Feed package provides a standardized interface for retrieving candlestick (OHLCV) data from various cryptocurrency exchanges. It supports:

- Real-time streaming of candle data via WebSockets
- Historical data retrieval via REST APIs
- A pluggable adapter system for easy integration with different exchanges
- Standardized data representation across exchanges

## Features

- **Modular Design**: Easily extend to support new exchanges
- **Multiple Transport Methods**: WebSocket for real-time data, REST for historical data
- **Built-in Throttling**: Respect exchange API rate limits
- **Efficient Data Processing**: Process and deduplicate candle data
- **Standardized Data Format**: Consistent candle representation across exchanges
- **Easy Integration**: Simple API for integration with trading strategies

## Supported Exchanges

- Binance Spot
- Bybit Spot
- Coinbase Advanced Trade
- Kraken Spot
- KuCoin Spot
- OKX Spot

## Installation

### As a standalone package

```bash
# Clone the repository
git clone https://github.com/MementoRC/hb-candles-feed.git

# Navigate to the candles-feed directory
cd hb-candles-feed

# Option 1: Install directly
pip install .

# Option 2: Install with development dependencies
pip install -e ".[dev]"

# Option 3: Use the development setup script (recommended)
./setup-dev-env.sh
```

### Building with Cython

This package uses Cython for performance-critical code. The Cython compilation is handled automatically during installation using scikit-build.

For manual compilation:

```bash
# Force recompilation of Cython modules
python cython_builder.py candles_feed
```

### As a dependency in your project

```bash
pip install hummingbot-candles-feed
```

## Quick Start

```python
import asyncio
from candles_feed.core.candles_feed import CandlesFeed

async def main():
    # Create a CandlesFeed instance
    feed = CandlesFeed(
        exchange="binance_spot",
        trading_pair="BTC-USDT",
        interval="1m",
        max_records=100
    )
    
    # Start the feed (uses WebSocket if available)
    await feed.start()
    
    # Wait for some data to arrive
    await asyncio.sleep(5)
    
    # Get the candles
    candles = feed.get_candles()
    for candle in candles:
        print(f"{candle.timestamp}: O={candle.open}, H={candle.high}, L={candle.low}, C={candle.close}, V={candle.volume}")
    
    # Stop the feed
    await feed.stop()

# Run the example
asyncio.run(main())
```

## Running the Tests

The package includes comprehensive unit, integration, and end-to-end tests using pytest.

### Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"
```

### Running Tests

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

We also provide a test runner script with additional options:

```bash
# Run all tests
./run_tests.py --all

# Run unit tests with coverage
./run_tests.py --unit --cov

# Run tests for a specific adapter
./run_tests.py --adapter=binance_spot
```

## Documentation

For more detailed documentation, see the [docs directory](./docs/).

## Contributing

Contributions are welcome! Please see the [contributing guide](./docs/contribution/) for more information.

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.