# Compatibility with Original CandlesFeed

This document describes the compatibility between the new Candles Feed implementation (in `hummingbot/sub-packages/candles-feed`) and the original implementation (in `origin/data_feed/candles_feed`).

## Overview

The new implementation maintains API compatibility with the original, while introducing a more modular architecture using adapters and composition patterns. This allows for easier maintenance, extension, and testing.

## Compatibility Features

### Constructor Parameters

The new `CandlesFeed` class accepts the same core parameters as the original:

```python
# Original
feed = CandlesBase(trading_pair="BTC-USDT", interval="1m", max_records=150)

# New
feed = CandlesFeed(exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=150)
```

The main difference is the addition of the `exchange` parameter, which is required to specify which exchange adapter to use.

### Core Methods

| Original CandlesBase | New CandlesFeed | Description |
|---------------------|-----------------|-------------|
| `start_network()` | `start()` | Initiates data collection |
| `stop_network()` | `stop()` | Stops data collection |
| `fetch_candles()` | `fetch_candles()` | Fetches historical candles |
| `get_historical_candles()` | `get_historical_candles()` | Fetches candles within time range |
| `fill_historical_candles()` | Handled internally | Fills candle store with historical data |
| `check_candles_sorted_and_equidistant()` | `check_candles_sorted_and_equidistant()` | Validates candle data |

### Properties and Attributes

| Original CandlesBase | New CandlesFeed | Description |
|---------------------|-----------------|-------------|
| `candles_df` | `get_candles_df()` | Returns DataFrame with candle data |
| `ready` | `ready` | Indicates if candle store is full |
| `trading_pair` | `trading_pair` | Trading pair in standard format |
| `ex_trading_pair` | `ex_trading_pair` | Trading pair in exchange-specific format |
| `interval` | `interval` | Candle interval (e.g., "1m") |
| `max_records` | `max_records` | Maximum number of candles to store |

### Data Format

The original implementation stored candles as arrays in a `deque`, while the new implementation uses the `CandleData` class. However, both convert to the same DataFrame format when accessed.

### Compatibility Implementation

To ensure compatibility, the new implementation includes:

1. The `check_candles_sorted_and_equidistant()` method to validate candle data
2. The `_round_timestamp_to_interval_multiple()` method for timestamp manipulation
3. A `get_historical_candles()` method that returns data in the same format
4. Compatible DataFrame column structure
5. WebSocket and REST polling strategies that match the original behavior
6. Support for Hummingbot components like AsyncThrottler and WebAssistantsFactory

## Usage Comparison

### Basic Usage

**Original:**
```python
from hummingbot.data_feed.candles_feed.binance_spot_candles import BinanceSpotCandles

candles = BinanceSpotCandles(trading_pair="BTC-USDT", interval="1m", max_records=100)
await candles.start_network()
df = candles.candles_df
await candles.stop_network()
```

**New:**
```python
from candles_feed.core.candles_feed import CandlesFeed

feed = CandlesFeed(exchange="binance_spot", trading_pair="BTC-USDT", interval="1m", max_records=100)
await feed.start()
df = feed.get_candles_df()
await feed.stop()
```

### Using Hummingbot Components

**Original:**
```python
# The original directly uses AsyncThrottler and WebAssistantsFactory

from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.data_feed.candles_feed.binance_spot_candles import BinanceSpotCandles

throttler = AsyncThrottler(rate_limits=[])
candles = BinanceSpotCandles(trading_pair="BTC-USDT", interval="1m", max_records=100)
# throttler is used internally
await candles.start_network()
```

**New:**
```python
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from candles_feed.core.candles_feed import CandlesFeed

throttler = AsyncThrottler(rate_limits=[])
web_assistants_factory = WebAssistantsFactory(throttler=throttler)

feed = CandlesFeed(
    exchange="binance_spot", 
    trading_pair="BTC-USDT", 
    interval="1m", 
    max_records=100,
    hummingbot_components={
        "throttler": throttler,
        "web_assistants_factory": web_assistants_factory,
    }
)
await feed.start()
```

## Migration Guide

To migrate from the original implementation to the new one:

1. Import `CandlesFeed` from `candles_feed.core.candles_feed` instead of the specific exchange class
2. Add the `exchange` parameter to specify which exchange adapter to use
3. Replace `start_network()` with `start()`
4. Replace `stop_network()` with `stop()`
5. Replace `candles_df` property access with `get_candles_df()` method call
6. If using Hummingbot components, pass them in the `hummingbot_components` dictionary

## Comprehensive Tests

The new implementation includes comprehensive tests to verify compatibility:

1. Unit tests for interface compatibility
2. Integration tests for behavioral compatibility
3. End-to-end tests with real exchange adapters

These tests ensure that the new implementation can be used as a drop-in replacement for the original, with the same behavior and data formats.