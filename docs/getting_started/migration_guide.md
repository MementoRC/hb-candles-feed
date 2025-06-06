# Migration Guide from Original Candles Feed

This guide helps you migrate from the original Hummingbot candles_feed implementation to the new sub-package architecture.

## Overview

The new candles-feed sub-package provides:

- **Enhanced Architecture**: Modular adapter system with clear separation of concerns
- **Improved Testing**: Comprehensive mock infrastructure for reliable testing
- **Better Performance**: Optimized connection pooling and resource management
- **Modern Python**: Type hints, async/await patterns, and Python 3.10+ features
- **Extensibility**: Plugin-based architecture for easy exchange integration

## Breaking Changes

### 1. Import Structure Changes

**Old (Original):**
```python
from hummingbot.data_feed.candles_feed.candles_feed import CandlesFeed
from hummingbot.data_feed.candles_feed.data_types import CandleData
```

**New (Sub-package):**
```python
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.candle_data import CandleData
```

### 2. Adapter Initialization

**Old (Original):**
```python
# Adapters were tightly coupled to Hummingbot infrastructure
adapter = BinanceSpotAdapter()
```

**New (Sub-package):**
```python
from candles_feed.adapters.binance import BinanceSpotAdapter
from candles_feed.core import NetworkClient, NetworkConfig

# Explicit dependency injection
config = NetworkConfig(
    rest_api_timeout=10.0,
    websocket_ping_interval=20.0
)
network_client = NetworkClient(config)

adapter = BinanceSpotAdapter(
    network_client=network_client,
    network_config=config
)
```

### 3. Configuration Structure

**Old (Original):**
```python
# Configuration was embedded in Hummingbot settings
connector_config = ConnectorConfiguration.inst()
```

**New (Sub-package):**
```python
from candles_feed.core import NetworkConfig

config = NetworkConfig(
    rest_api_timeout=10.0,
    websocket_ping_interval=20.0,
    max_connections_per_host=100,
    enable_connection_pooling=True
)
```

### 4. Exchange Registry

**Old (Original):**
```python
# Registry was part of Hummingbot's global state
```

**New (Sub-package):**
```python
from candles_feed.core import ExchangeRegistry

registry = ExchangeRegistry()
registry.register_adapter("binance_spot", BinanceSpotAdapter)
adapter = registry.get_adapter("binance_spot", network_client, config)
```

## Step-by-Step Migration

### Step 1: Update Dependencies

**Update pyproject.toml or requirements.txt:**
```toml
[project]
dependencies = [
    "hb-candles-feed>=1.0.0",  # New sub-package
    # Remove old hummingbot dependency for candles_feed if using standalone
]
```

### Step 2: Update Imports

Create a migration script to update all imports:

```python
# migration_helper.py
import re
from pathlib import Path

def migrate_imports(file_path: Path):
    """Update imports in a Python file."""
    content = file_path.read_text()
    
    # Migration mappings
    migrations = {
        r'from hummingbot\.data_feed\.candles_feed\.candles_feed import': 
            'from candles_feed.core.candles_feed import',
        r'from hummingbot\.data_feed\.candles_feed\.data_types import': 
            'from candles_feed.core.candle_data import',
        r'from hummingbot\.data_feed\.candles_feed\.(.+) import': 
            r'from candles_feed.adapters.\1 import',
    }
    
    for old_pattern, new_pattern in migrations.items():
        content = re.sub(old_pattern, new_pattern, content)
    
    file_path.write_text(content)

# Usage
for py_file in Path('.').rglob('*.py'):
    migrate_imports(py_file)
```

### Step 3: Update Adapter Usage

**Old Pattern:**
```python
class MyTradingStrategy:
    def __init__(self):
        self.candles_feed = CandlesFeed.get_instance()
        
    async def get_candles(self):
        return await self.candles_feed.get_candles(
            connector="binance",
            trading_pair="BTC-USDT",
            interval="1m"
        )
```

**New Pattern:**
```python
class MyTradingStrategy:
    def __init__(self):
        # Create network infrastructure
        self.config = NetworkConfig(
            rest_api_timeout=10.0,
            websocket_ping_interval=20.0
        )
        self.network_client = NetworkClient(self.config)
        
        # Initialize exchange registry
        self.registry = ExchangeRegistry()
        self._register_adapters()
        
        # Create candles feed
        self.candles_feed = CandlesFeed(
            network_client=self.network_client,
            exchange_registry=self.registry
        )
    
    def _register_adapters(self):
        from candles_feed.adapters.binance import BinanceSpotAdapter
        self.registry.register_adapter("binance_spot", BinanceSpotAdapter)
        
    async def get_candles(self):
        return await self.candles_feed.get_candles(
            exchange="binance_spot",
            trading_pair="BTCUSDT",  # Note: format change
            interval="1m"
        )
```

### Step 4: Update Configuration

**Old Configuration:**
```python
# Was part of Hummingbot global config
```

**New Configuration:**
```python
from candles_feed.core import NetworkConfig

# Create explicit configuration
config = NetworkConfig(
    rest_api_timeout=10.0,
    websocket_ping_interval=20.0,
    max_connections_per_host=100,
    enable_connection_pooling=True,
    request_retry_attempts=3,
    websocket_reconnect_attempts=5
)
```

### Step 5: Update Error Handling

**Old Error Handling:**
```python
try:
    candles = await adapter.get_candles("BTC-USDT", "1m")
except Exception as e:
    logger.error(f"Failed to get candles: {e}")
```

**New Error Handling:**
```python
from candles_feed.adapters.base_adapter import AdapterError, NetworkError

try:
    candles = await adapter.get_candles("BTCUSDT", "1m")
except NetworkError as e:
    logger.error(f"Network error: {e}")
    # Implement retry logic
except AdapterError as e:
    logger.error(f"Adapter error: {e}")
    # Handle adapter-specific issues
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Trading Pair Format Changes

### Format Mapping

| Exchange | Old Format | New Format |
|----------|------------|------------|
| Binance | BTC-USDT | BTCUSDT |
| Coinbase | BTC-USD | BTC-USD |
| Bybit | BTC-USDT | BTCUSDT |
| Kraken | XBT-USD | XBTUSD |

### Conversion Helper

```python
def convert_trading_pair_format(pair: str, exchange: str) -> str:
    """Convert trading pair to exchange-specific format."""
    mapping = {
        "binance": lambda p: p.replace("-", ""),
        "bybit": lambda p: p.replace("-", ""),
        "coinbase": lambda p: p,  # No change
        "kraken": lambda p: p.replace("-", "").replace("BTC", "XBT")
    }
    
    converter = mapping.get(exchange.lower())
    return converter(pair) if converter else pair
```

## Testing Migration

### Old Test Pattern

```python
class TestCandlesFeed(unittest.TestCase):
    def setUp(self):
        self.candles_feed = CandlesFeed.get_instance()
    
    def test_get_candles(self):
        # Tests relied on real API calls or complex mocking
        pass
```

### New Test Pattern

```python
import pytest
from candles_feed.mocking_resources import AsyncMockedAdapter, MockServer
from candles_feed.core import NetworkClient, NetworkConfig

class TestCandlesFeed:
    @pytest.fixture
    async def mock_adapter(self):
        config = NetworkConfig()
        network_client = NetworkClient(config)
        
        adapter = AsyncMockedAdapter(
            network_client=network_client,
            network_config=config,
            exchange_name="binance",
            trading_pair="BTCUSDT"
        )
        return adapter
    
    @pytest.mark.asyncio
    async def test_get_candles(self, mock_adapter):
        candles = await mock_adapter.get_candles("BTCUSDT", "1m", limit=10)
        assert len(candles) == 10
        assert all(candle.trading_pair == "BTCUSDT" for candle in candles)
```

## Integration with Hummingbot

### As a Sub-package

```python
# In your Hummingbot strategy
from candles_feed.integration import HummingbotCandlesFeed
from candles_feed.core import NetworkConfig

class MyStrategy(StrategyPy):
    def __init__(self):
        # Initialize with Hummingbot integration
        config = NetworkConfig(
            # Use Hummingbot's existing network settings
            rest_api_timeout=self.connector_config.rest_api_timeout
        )
        
        self.candles_feed = HummingbotCandlesFeed(
            network_config=config,
            hummingbot_app=self.app  # Pass Hummingbot app reference
        )
    
    async def get_market_data(self):
        return await self.candles_feed.get_candles(
            exchange="binance_spot",
            trading_pair="BTCUSDT",
            interval="1m"
        )
```

### Standalone Usage

```python
# For non-Hummingbot applications
from candles_feed.core import CandlesFeed, NetworkClient, NetworkConfig, ExchangeRegistry
from candles_feed.adapters.binance import BinanceSpotAdapter

async def main():
    # Create standalone candles feed
    config = NetworkConfig()
    network_client = NetworkClient(config)
    
    registry = ExchangeRegistry()
    registry.register_adapter("binance_spot", BinanceSpotAdapter)
    
    candles_feed = CandlesFeed(
        network_client=network_client,
        exchange_registry=registry
    )
    
    # Use normally
    candles = await candles_feed.get_candles(
        exchange="binance_spot",
        trading_pair="BTCUSDT",
        interval="1m"
    )
    
    print(f"Retrieved {len(candles)} candles")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Performance Considerations

### Connection Pooling

**Old (Limited):**
```python
# Connection pooling was implicit and limited
```

**New (Configurable):**
```python
config = NetworkConfig(
    enable_connection_pooling=True,
    max_connections_per_host=100,
    connection_pool_size=50
)
```

### Resource Management

**Old Pattern:**
```python
# Manual resource cleanup required
try:
    adapter = BinanceAdapter()
    candles = await adapter.get_candles("BTC-USDT", "1m")
finally:
    # Manual cleanup
    pass
```

**New Pattern:**
```python
# Automatic resource management
async with NetworkClient(config) as network_client:
    adapter = BinanceSpotAdapter(
        network_client=network_client,
        network_config=config
    )
    candles = await adapter.get_candles("BTCUSDT", "1m")
    # Automatic cleanup on exit
```

## Common Migration Issues

### 1. Import Errors

**Issue:** `ModuleNotFoundError: No module named 'hummingbot.data_feed.candles_feed'`

**Solution:** Update all imports to use the new sub-package structure.

### 2. Trading Pair Format

**Issue:** Exchange APIs reject trading pair formats.

**Solution:** Use the format conversion helper or check exchange documentation.

### 3. Configuration Missing

**Issue:** `AttributeError: 'NoneType' object has no attribute 'rest_api_timeout'`

**Solution:** Explicitly create NetworkConfig instead of relying on global configuration.

### 4. Async Context Issues

**Issue:** `RuntimeError: cannot be called from a running event loop`

**Solution:** Ensure proper async context management and use `async with` patterns.

## Validation Checklist

- [ ] All imports updated to new sub-package structure
- [ ] Trading pair formats converted for each exchange
- [ ] NetworkConfig explicitly created
- [ ] Error handling updated to use new exception types
- [ ] Tests migrated to use mock infrastructure
- [ ] Configuration validated and tested
- [ ] Performance benchmarks meet requirements
- [ ] Integration tests pass with new architecture

## Getting Help

If you encounter issues during migration:

1. **Check Documentation**: Review the [API Reference](../api_reference/core.md)
2. **Review Examples**: See [Usage Examples](../examples/simple_usage.md)
3. **Test Infrastructure**: Use [Mock Server](../testing_resources/mock_server.md) for testing
4. **Community Support**: Join the Hummingbot Discord for migration assistance

The new architecture provides better separation of concerns, improved testability, and enhanced performance while maintaining compatibility with existing Hummingbot strategies.