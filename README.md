# hb-candles-feed

Exchange candles (OHLCV) data feed for hummingbot sub-packages.

## Overview

Independent candles feed module extracted from hummingbot's monolith. Provides real-time and historical OHLCV candlestick data from multiple exchanges via REST and WebSocket connections.

## Features

- Multi-exchange support (Binance, Bybit, Coinbase, and more)
- REST polling and WebSocket streaming strategies
- Plugin-based exchange adapter architecture
- Drop-in replacement for hummingbot via `hb_compat` layer
- Comprehensive mocking infrastructure for testing

## Installation

```bash
pixi install
```

## Usage

```python
from candles_feed import CandlesFeed

feed = CandlesFeed(exchange="binance_spot", trading_pair="BTC-USDT", interval="1m")
await feed.start()
candles = feed.candles_df
```

## Development

```bash
pixi run check    # lint + format + test
pixi run test     # run all tests
pixi run lint     # ruff check
pixi run format   # ruff format
```

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.
