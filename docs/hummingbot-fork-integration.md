# Hummingbot Fork Integration Guide

This guide explains how to integrate `hb-candles-feed` as a drop-in replacement for
hummingbot's built-in candles subsystem.

## Prerequisites

- A fork of [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot)
- `hb-candles-feed` installed (see Installation below)

## Installation

Install `hb-candles-feed` as an editable dependency in your hummingbot environment:

```bash
# From your hummingbot fork root
pip install -e /path/to/candles-feed
```

Or add to your `setup.py` / `pyproject.toml` dependencies:

```
candles-feed @ git+https://github.com/MementoRC/hb-candles-feed.git@main
```

## File Changes

Three files need modification in your hummingbot fork.

### 1. `hummingbot/data_feed/candles_feed/candles_factory.py`

**Before:**
```python
from hummingbot.data_feed.candles_feed.binance_perpetual_candles import BinancePerpetualCandles
from hummingbot.data_feed.candles_feed.binance_spot_candles import BinanceSpotCandles
# ... many more imports ...

class CandlesFactory:
    _candles_map = {
        "binance": BinanceSpotCandles,
        "binance_perpetual": BinancePerpetualCandles,
        # ... many more entries ...
    }

    @classmethod
    def get_candle(cls, candles_config: CandlesConfig):
        # ... complex instantiation logic ...
```

**After:**
```python
from candles_feed.hb_compat import CandlesFactory as HBCandlesFactory, CandlesConfig

# Re-export for backward compatibility
CandlesFactory = HBCandlesFactory
```

### 2. `hummingbot/data_feed/candles_feed/data_types.py`

**Before:**
```python
from dataclasses import dataclass

@dataclass
class CandlesConfig:
    connector: str
    trading_pair: str
    interval: str = "1m"
    max_records: int = 500

# ... other types ...
```

**After:**
```python
from candles_feed.hb_compat import (
    CandlesConfig,
    HistoricalCandlesConfig,
    UnsupportedConnectorException,
)

# Re-export for backward compatibility — existing imports still work
__all__ = ["CandlesConfig", "HistoricalCandlesConfig", "UnsupportedConnectorException"]
```

### 3. `hummingbot/data_feed/market_data_provider.py`

This is the main consumer. Key changes:

**Before (get_historical_candles_df):**
```python
async def get_historical_candles_df(self, config: HistoricalCandlesConfig) -> pd.DataFrame:
    candle_feed = self._candles[candle_key]
    candle_feed._candles = deque(maxlen=config.max_records)  # Direct deque access
    candles = await candle_feed.fetch_candles(...)
    candle_feed._candles.extend(candles)
    return candle_feed.candles_df
```

**After:**
```python
async def get_historical_candles_df(self, config: HistoricalCandlesConfig) -> pd.DataFrame:
    candle_feed = self._candles[candle_key]
    df = await candle_feed.get_historical_candles(config)
    candle_feed.reset_with_dataframe(df)  # Uses adapter method instead of deque access
    return candle_feed.candles_df
```

## Legacy Fallback Pattern

For exchanges not yet supported by `hb-candles-feed`, use a fallback pattern:

```python
from candles_feed.hb_compat import CandlesFactory, CandlesConfig, UnsupportedConnectorException

# Import original factory as fallback
from hummingbot.data_feed.candles_feed._original_candles_factory import OriginalCandlesFactory

class HybridCandlesFactory:
    @classmethod
    def get_candle(cls, config: CandlesConfig):
        try:
            return CandlesFactory.get_candle(config)
        except UnsupportedConnectorException:
            # Fall back to hummingbot's built-in implementation
            return OriginalCandlesFactory.get_candle(config)
```

### Supported Connectors

| Connector | Status |
|-----------|--------|
| `binance` (spot) | Supported |
| `binance_perpetual` | Supported |
| `bybit` (spot) | Supported |
| `coinbase_advanced_trade` | Supported |
| `kraken` (spot) | Supported |
| `kucoin` (spot) | Supported |
| `okx` (spot) | Supported |

## Testing

### Verify installation

```python
python -c "from candles_feed.hb_compat import CandlesFactory; print('OK')"
```

### Verify connector mapping

```python
from candles_feed.hb_compat import CandlesFactory, CandlesConfig

config = CandlesConfig(connector="binance", trading_pair="BTC-USDT", interval="1m")
candle = CandlesFactory.get_candle(config)
print(f"Name: {candle.name}")           # binance_spot
print(f"Interval: {candle.interval}")    # 1m
print(f"Ready: {candle.ready}")          # False (no data yet)
```

### Run hummingbot's existing candle tests

After making the file changes above, run hummingbot's test suite to verify
backward compatibility:

```bash
pytest tests/hummingbot/data_feed/candles_feed/ -v
```
