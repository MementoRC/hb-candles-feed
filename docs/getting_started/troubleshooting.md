# Troubleshooting Guide

This guide helps you resolve common issues when working with the candles-feed sub-package.

## Common Issues and Solutions

### 1. Import and Module Errors

#### ModuleNotFoundError: No module named 'candles_feed'

**Symptoms:**
```
ModuleNotFoundError: No module named 'candles_feed'
ModuleNotFoundError: No module named 'candles_feed.core'
```

**Causes:**
- Package not installed
- Virtual environment not activated
- Incorrect Python path

**Solutions:**

1. **Install the package:**
   ```bash
   pip install hb-candles-feed
   # or for development
   pip install -e .
   ```

2. **Check virtual environment:**
   ```bash
   # Verify you're in the correct environment
   which python
   pip list | grep candles-feed
   ```

3. **Verify installation:**
   ```python
   import candles_feed
   print(candles_feed.__version__)
   ```

#### Import path conflicts

**Symptoms:**
```
ImportError: cannot import name 'CandlesFeed' from 'candles_feed.core'
AttributeError: module 'candles_feed' has no attribute 'core'
```

**Solutions:**

1. **Check import structure:**
   ```python
   # Correct imports
   from candles_feed.core.candles_feed import CandlesFeed
   from candles_feed.core.candle_data import CandleData
   from candles_feed.adapters.binance import BinanceSpotAdapter
   
   # Incorrect imports
   from candles_feed import CandlesFeed  # Wrong
   import candles_feed.core as core      # Ambiguous
   ```

2. **Clear Python cache:**
   ```bash
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} +
   ```

### 2. Network and Connection Issues

#### Connection timeout errors

**Symptoms:**
```
aiohttp.ServerTimeoutError: Timeout on reading data from socket
asyncio.TimeoutError: Request timed out
```

**Causes:**
- Network connectivity issues
- Exchange API rate limiting
- Incorrect timeout configuration

**Solutions:**

1. **Increase timeout values:**
   ```python
   from candles_feed.core import NetworkConfig
   
   config = NetworkConfig(
       rest_api_timeout=30.0,  # Increase from default 10.0
       websocket_ping_interval=60.0,  # Increase from default 20.0
       connection_timeout=15.0
   )
   ```

2. **Check network connectivity:**
   ```python
   import asyncio
   import aiohttp
   
   async def test_connectivity():
       async with aiohttp.ClientSession() as session:
           try:
               async with session.get('https://api.binance.com/api/v3/ping') as response:
                   print(f"Binance API: {response.status}")
           except Exception as e:
               print(f"Connection failed: {e}")
   
   asyncio.run(test_connectivity())
   ```

3. **Implement retry logic:**
   ```python
   import asyncio
   from candles_feed.adapters.base_adapter import NetworkError
   
   async def get_candles_with_retry(adapter, trading_pair, interval, max_retries=3):
       for attempt in range(max_retries):
           try:
               return await adapter.get_candles(trading_pair, interval)
           except NetworkError as e:
               if attempt == max_retries - 1:
                   raise
               print(f"Attempt {attempt + 1} failed: {e}")
               await asyncio.sleep(2 ** attempt)  # Exponential backoff
   ```

#### Rate limiting issues

**Symptoms:**
```
HTTP 429: Too Many Requests
Rate limit exceeded
API rate limit reached
```

**Solutions:**

1. **Configure rate limiting:**
   ```python
   config = NetworkConfig(
       requests_per_second=5,  # Reduce request rate
       burst_requests=10,
       rate_limit_buffer=0.1
   )
   ```

2. **Use connection pooling:**
   ```python
   config = NetworkConfig(
       enable_connection_pooling=True,
       max_connections_per_host=10,
       connection_pool_size=50
   )
   ```

3. **Implement request throttling:**
   ```python
   import asyncio
   from asyncio import Semaphore
   
   class ThrottledAdapter:
       def __init__(self, adapter, max_concurrent=5):
           self.adapter = adapter
           self.semaphore = Semaphore(max_concurrent)
       
       async def get_candles(self, *args, **kwargs):
           async with self.semaphore:
               return await self.adapter.get_candles(*args, **kwargs)
   ```

### 3. Exchange-Specific Issues

#### Trading pair format errors

**Symptoms:**
```
InvalidTradingPair: Unknown trading pair format
Symbol not found: BTC-USDT
API error: Invalid symbol
```

**Solutions:**

1. **Use correct trading pair formats:**
   ```python
   # Exchange-specific formats
   formats = {
       "binance": "BTCUSDT",      # No separator
       "coinbase": "BTC-USD",     # Hyphen separator  
       "bybit": "BTCUSDT",        # No separator
       "kraken": "XBTUSD",        # Different base currency code
       "gate_io": "BTC_USDT",     # Underscore separator
   }
   ```

2. **Convert trading pairs:**
   ```python
   def normalize_trading_pair(pair: str, exchange: str) -> str:
       """Convert trading pair to exchange format."""
       # Remove common separators
       base_pair = pair.replace("-", "").replace("_", "").upper()
       
       exchange_formats = {
           "binance": lambda p: p,
           "coinbase": lambda p: p[:3] + "-" + p[3:],
           "kraken": lambda p: p.replace("BTC", "XBT"),
           "gate_io": lambda p: p[:3] + "_" + p[3:],
       }
       
       formatter = exchange_formats.get(exchange.lower())
       return formatter(base_pair) if formatter else base_pair
   ```

#### Exchange API changes

**Symptoms:**
```
KeyError: 'data' not found in response
Unexpected response format
API version deprecated
```

**Solutions:**

1. **Check adapter version compatibility:**
   ```python
   from candles_feed.adapters.binance import BinanceSpotAdapter
   
   print(f"Adapter version: {BinanceSpotAdapter.__version__}")
   print(f"Supported API version: {BinanceSpotAdapter.API_VERSION}")
   ```

2. **Enable debug logging:**
   ```python
   import logging
   
   logging.basicConfig(level=logging.DEBUG)
   logger = logging.getLogger('candles_feed')
   logger.setLevel(logging.DEBUG)
   ```

3. **Use mock adapters for testing:**
   ```python
   from candles_feed.mocking_resources.adapter import AsyncMockedAdapter
   
   # Test with mock adapter first
   mock_adapter = AsyncMockedAdapter(
       network_client=network_client,
       network_config=config,
       exchange_name="binance",
       trading_pair="BTCUSDT"
   )
   ```

### 4. Data and Type Issues

#### CandleData validation errors

**Symptoms:**
```
ValidationError: Invalid candle data format
TypeError: Expected CandleData, got dict
ValueError: Timestamp must be datetime object
```

**Solutions:**

1. **Validate data before processing:**
   ```python
   from candles_feed.core.candle_data import CandleData
   from datetime import datetime
   
   def validate_candle_data(data):
       required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
       
       if isinstance(data, dict):
           # Validate dictionary format
           missing = [f for f in required_fields if f not in data]
           if missing:
               raise ValueError(f"Missing fields: {missing}")
           
           # Convert to CandleData
           return CandleData(
               timestamp=datetime.fromtimestamp(data['timestamp']),
               open=float(data['open']),
               high=float(data['high']),
               low=float(data['low']),
               close=float(data['close']),
               volume=float(data['volume']),
               trading_pair=data.get('trading_pair', 'UNKNOWN')
           )
       
       return data
   ```

2. **Handle timestamp formats:**
   ```python
   from datetime import datetime
   
   def parse_timestamp(ts):
       """Parse various timestamp formats."""
       if isinstance(ts, datetime):
           return ts
       elif isinstance(ts, (int, float)):
           # Unix timestamp (seconds or milliseconds)
           if ts > 1e10:  # Milliseconds
               return datetime.fromtimestamp(ts / 1000)
           else:  # Seconds
               return datetime.fromtimestamp(ts)
       elif isinstance(ts, str):
           # ISO format string
           return datetime.fromisoformat(ts.replace('Z', '+00:00'))
       else:
           raise ValueError(f"Unknown timestamp format: {type(ts)}")
   ```

#### DataFrame conversion issues

**Symptoms:**
```
ValueError: Cannot convert to DataFrame
KeyError: Expected column not found
TypeError: Invalid data type for pandas
```

**Solutions:**

1. **Convert CandleData to DataFrame:**
   ```python
   import pandas as pd
   from candles_feed.core.candle_data import CandleData
   
   def candles_to_dataframe(candles: list[CandleData]) -> pd.DataFrame:
       """Convert CandleData list to pandas DataFrame."""
       if not candles:
           return pd.DataFrame()
       
       data = []
       for candle in candles:
           data.append({
               'timestamp': candle.timestamp,
               'open': candle.open,
               'high': candle.high,
               'low': candle.low,
               'close': candle.close,
               'volume': candle.volume,
               'trading_pair': candle.trading_pair
           })
       
       df = pd.DataFrame(data)
       df.set_index('timestamp', inplace=True)
       return df
   ```

2. **Handle missing or invalid data:**
   ```python
   def clean_candle_data(candles):
       """Clean and validate candle data."""
       cleaned = []
       for candle in candles:
           try:
               # Validate numeric fields
               if all(isinstance(getattr(candle, field), (int, float)) 
                      for field in ['open', 'high', 'low', 'close', 'volume']):
                   # Validate OHLC logic
                   if candle.high >= max(candle.open, candle.close) and \
                      candle.low <= min(candle.open, candle.close):
                       cleaned.append(candle)
           except (AttributeError, TypeError) as e:
               print(f"Skipping invalid candle: {e}")
       
       return cleaned
   ```

### 5. Async and Concurrency Issues

#### Event loop errors

**Symptoms:**
```
RuntimeError: asyncio.run() cannot be called from a running event loop
RuntimeError: There is no current event loop in thread
```

**Solutions:**

1. **Check event loop context:**
   ```python
   import asyncio
   
   def run_async_function(coro):
       """Run async function in appropriate context."""
       try:
           # Try to get current loop
           loop = asyncio.get_running_loop()
           # If we're in a loop, create a task
           return loop.create_task(coro)
       except RuntimeError:
           # No running loop, create one
           return asyncio.run(coro)
   ```

2. **Use proper async context managers:**
   ```python
   async def get_candles_properly():
       config = NetworkConfig()
       
       async with NetworkClient(config) as network_client:
           adapter = BinanceSpotAdapter(
               network_client=network_client,
               network_config=config
           )
           
           candles = await adapter.get_candles("BTCUSDT", "1m")
           return candles
   ```

#### Resource cleanup issues

**Symptoms:**
```
ResourceWarning: unclosed <ssl.SSLSocket>
RuntimeWarning: coroutine was never awaited
UserWarning: Unclosed client session
```

**Solutions:**

1. **Ensure proper cleanup:**
   ```python
   async def safe_candles_fetch():
       config = NetworkConfig()
       network_client = None
       adapter = None
       
       try:
           network_client = NetworkClient(config)
           adapter = BinanceSpotAdapter(
               network_client=network_client,
               network_config=config
           )
           
           candles = await adapter.get_candles("BTCUSDT", "1m")
           return candles
           
       finally:
           # Explicit cleanup
           if adapter:
               await adapter.close()
           if network_client:
               await network_client.close()
   ```

2. **Use context managers:**
   ```python
   from contextlib import asynccontextmanager
   
   @asynccontextmanager
   async def candles_adapter(exchange: str):
       config = NetworkConfig()
       
       async with NetworkClient(config) as network_client:
           if exchange == "binance":
               adapter = BinanceSpotAdapter(
                   network_client=network_client,
                   network_config=config
               )
           else:
               raise ValueError(f"Unknown exchange: {exchange}")
           
           try:
               yield adapter
           finally:
               await adapter.close()
   
   # Usage
   async with candles_adapter("binance") as adapter:
       candles = await adapter.get_candles("BTCUSDT", "1m")
   ```

### 6. Testing and Mock Issues

#### Mock server not responding

**Symptoms:**
```
ConnectionRefusedError: [Errno 111] Connection refused
aiohttp.ClientConnectorError: Cannot connect to host 127.0.0.1:8080
```

**Solutions:**

1. **Check mock server status:**
   ```python
   from candles_feed.mocking_resources.core import MockServer
   from candles_feed.mocking_resources.exchange_server_plugins.binance import BinanceSpotPlugin
   
   async def test_mock_server():
       server = MockServer(port=8080)
       server.add_plugin(BinanceSpotPlugin())
       
       try:
           await server.start()
           print("Mock server started successfully")
           
           # Test connection
           import aiohttp
           async with aiohttp.ClientSession() as session:
               async with session.get('http://127.0.0.1:8080/api/v3/ping') as response:
                   print(f"Server responded with status: {response.status}")
                   
       except Exception as e:
           print(f"Mock server failed: {e}")
       finally:
           await server.stop()
   ```

2. **Use different port if needed:**
   ```python
   import socket
   
   def find_free_port():
       """Find a free port for the mock server."""
       with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
           s.bind(('', 0))
           s.listen(1)
           port = s.getsockname()[1]
       return port
   
   # Use dynamic port
   port = find_free_port()
   server = MockServer(port=port)
   ```

#### Mock data inconsistencies

**Symptoms:**
```
AssertionError: Expected 100 candles, got 95
ValueError: Mock data doesn't match expected format
```

**Solutions:**

1. **Configure mock data generation:**
   ```python
   from candles_feed.mocking_resources.core import CandleDataFactory
   from datetime import datetime, timedelta
   
   factory = CandleDataFactory()
   
   # Generate consistent test data
   start_time = datetime(2023, 1, 1, 0, 0, 0)
   end_time = start_time + timedelta(hours=1)
   
   candles = factory.generate_candles(
       start_time=start_time,
       end_time=end_time,
       interval="1m",
       base_price=50000.0,
       volatility=0.01,  # Low volatility for predictable data
       ensure_count=60   # Exactly 60 candles for 1 hour
   )
   ```

2. **Validate mock data:**
   ```python
   def validate_mock_candles(candles, expected_count=None):
       """Validate mock candle data consistency."""
       if expected_count and len(candles) != expected_count:
           raise ValueError(f"Expected {expected_count} candles, got {len(candles)}")
       
       # Check chronological order
       for i in range(1, len(candles)):
           if candles[i].timestamp <= candles[i-1].timestamp:
               raise ValueError(f"Candles not in chronological order at index {i}")
       
       # Check OHLC validity
       for i, candle in enumerate(candles):
           if not (candle.low <= min(candle.open, candle.close) <= 
                   max(candle.open, candle.close) <= candle.high):
               raise ValueError(f"Invalid OHLC data at index {i}")
       
       return True
   ```

## Debugging Tools

### 1. Enable Debug Logging

```python
import logging

# Enable debug logging for the entire package
logging.basicConfig(level=logging.DEBUG)

# Or be more specific
logger = logging.getLogger('candles_feed')
logger.setLevel(logging.DEBUG)

# Add handler for file output
handler = logging.FileHandler('candles_feed_debug.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
```

### 2. Network Request Inspection

```python
import aiohttp
import logging

# Enable aiohttp debug logging
logging.getLogger('aiohttp.client').setLevel(logging.DEBUG)

# Or use custom trace configuration
async def debug_request(session, trace_config_ctx, params):
    print(f"Starting request: {params.method} {params.url}")

async def debug_response(session, trace_config_ctx, params):
    print(f"Response: {params.response.status} for {params.url}")

trace_config = aiohttp.TraceConfig()
trace_config.on_request_start.append(debug_request)
trace_config.on_request_end.append(debug_response)

# Use in NetworkClient
config = NetworkConfig(trace_configs=[trace_config])
```

### 3. Performance Monitoring

```python
import time
from functools import wraps

def monitor_performance(func):
    """Decorator to monitor function performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            print(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            print(f"{func.__name__} failed after {duration:.2f}s: {e}")
            raise
    return wrapper

# Apply to adapter methods
@monitor_performance
async def get_candles_monitored(adapter, *args, **kwargs):
    return await adapter.get_candles(*args, **kwargs)
```

## Getting Additional Help

### 1. Check Documentation
- [API Reference](../api_reference/core.md)
- [Usage Examples](../examples/simple_usage.md)
- [Architecture Guide](architecture.md)

### 2. Enable Verbose Output
```python
import os
os.environ['CANDLES_FEED_DEBUG'] = '1'
os.environ['CANDLES_FEED_VERBOSE'] = '1'
```

### 3. Common Debug Commands

```bash
# Check package installation
pip show hb-candles-feed

# Run package diagnostics
python -c "import candles_feed; candles_feed.run_diagnostics()"

# Test network connectivity
python -c "import asyncio; from candles_feed.utils import test_exchange_connectivity; asyncio.run(test_exchange_connectivity())"

# Validate configuration
python -c "from candles_feed.core import NetworkConfig; config = NetworkConfig(); config.validate()"
```

### 4. Issue Reporting

When reporting issues, include:

1. **Environment information:**
   ```python
   import sys
   import candles_feed
   import aiohttp
   import pandas as pd
   
   print(f"Python: {sys.version}")
   print(f"candles-feed: {candles_feed.__version__}")
   print(f"aiohttp: {aiohttp.__version__}")
   print(f"pandas: {pd.__version__}")
   ```

2. **Minimal reproducible example**
3. **Full error traceback**
4. **Configuration used**
5. **Network/exchange being accessed**

This comprehensive troubleshooting guide should help resolve most common issues encountered when using the candles-feed sub-package.