# Exchange Adapters API Reference

This page documents the exchange adapter classes and their APIs for connecting to various cryptocurrency exchanges.

## Base Adapter Classes

### BaseAdapter

::: candles_feed.adapters.base_adapter.BaseAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

### Adapter Mixins

::: candles_feed.adapters.adapter_mixins.TestnetSupportMixin
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

::: candles_feed.adapters.adapter_mixins.NoWebSocketSupportMixin
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

::: candles_feed.adapters.adapter_mixins.SyncOnlyAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

::: candles_feed.adapters.adapter_mixins.AsyncOnlyAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

## Core Exchange Adapters

The candles-feed framework supports multiple cryptocurrency exchanges through a unified adapter interface.

### Binance

::: candles_feed.adapters.binance.base_adapter.BinanceBaseAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

::: candles_feed.adapters.binance.spot_adapter.BinanceSpotAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

::: candles_feed.adapters.binance.perpetual_adapter.BinancePerpetualAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

### Bybit

::: candles_feed.adapters.bybit.base_adapter.BybitBaseAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

::: candles_feed.adapters.bybit.spot_adapter.BybitSpotAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

### Coinbase Advanced Trade

::: candles_feed.adapters.coinbase_advanced_trade.base_adapter.CoinbaseAdvancedTradeBaseAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

::: candles_feed.adapters.coinbase_advanced_trade.spot_adapter.CoinbaseAdvancedTradeSpotAdapter
    handler: python
    selection:
      docstring_style: restructured-text
    rendering:
      show_source: true
      show_if_no_docstring: false
      heading_level: 3

## Usage Examples

### Basic Adapter Usage

```python
from candles_feed.adapters.binance import BinanceSpotAdapter
from candles_feed.core import NetworkClient, NetworkConfig

# Create network configuration
config = NetworkConfig(
    rest_api_timeout=10.0,
    websocket_ping_interval=20.0
)

# Initialize network client
network_client = NetworkClient(config)

# Create adapter
adapter = BinanceSpotAdapter(
    network_client=network_client,
    network_config=config
)

# Fetch candle data
candles = await adapter.fetch_rest_candles("BTCUSDT", "1m", limit=100)
```

### WebSocket Streaming

```python
async def handle_candle_update(candle_data):
    print(f"New candle: {candle_data}")

# Start WebSocket stream (where supported)
stream = adapter.start_websocket_stream("BTCUSDT", "1m")
async for candle in stream:
    handle_candle_update(candle)
```

### Error Handling

```python
from candles_feed.adapters.base_adapter import AdapterError
from candles_feed.core.network_client import NetworkError

try:
    candles = await adapter.fetch_rest_candles("INVALID_PAIR", "1m")
except NetworkError as e:
    print(f"Network error: {e}")
except AdapterError as e:
    print(f"Adapter error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Testnet Support

```python
# Many adapters support testnet mode
config = NetworkConfig(
    testnet_mode=True,  # Enable testnet
    rest_api_timeout=10.0
)

adapter = BinanceSpotAdapter(
    network_client=network_client,
    network_config=config
)

# Adapter will automatically use testnet endpoints
candles = await adapter.fetch_rest_candles("BTCUSDT", "1m")
```

## Additional Exchange Support

The framework includes adapters for additional exchanges:

- **Kraken**: Spot trading support
- **Gate.io**: Spot and perpetual trading
- **OKX**: Comprehensive spot and perpetual support
- **KuCoin**: Spot and perpetual trading
- **Hyperliquid**: Advanced perpetual trading
- **MEXC**: Spot and perpetual trading
- **AscendEX**: Spot trading support

For complete API documentation of additional exchanges, refer to the source code or use Python's built-in help system:

```python
from candles_feed.adapters.kraken import KrakenSpotAdapter
help(KrakenSpotAdapter)
```

## Framework Design

All adapters inherit from `BaseAdapter` and implement a consistent interface:

- **REST API Support**: `fetch_rest_candles()` method
- **WebSocket Support**: Available where exchange supports it
- **Testnet Integration**: Automatic testnet URL switching
- **Error Handling**: Consistent exception hierarchy
- **Type Safety**: Full type annotations for better development experience

The mixin system allows for code reuse and consistent behavior across all exchange adapters while maintaining the flexibility to implement exchange-specific features.
