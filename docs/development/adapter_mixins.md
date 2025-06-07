# Exchange Adapter Mixins

This document explains the mixin-based composition pattern used in the candles-feed package for creating exchange adapters.

## Introduction to the Mixin Pattern

The adapter mixins provide a flexible way to compose exchange adapter behavior. Each mixin handles a specific aspect of exchange interaction, such as trading pair formatting, timestamp handling, or response parsing. By combining these mixins, you can create adapters for new exchanges with minimal code.

## Mixin Types

The package provides the following mixin types:

1. **Trading Pair Formatters** - Convert between standard format (BTC-USDT) and exchange-specific formats
2. **Timestamp Handlers** - Convert between internal timestamps (seconds) and exchange-specific formats
3. **WebSocket Subscription Handlers** - Create subscription messages for real-time data
4. **REST Parameter Handlers** - Format parameters for REST API requests
5. **Response Parsers** - Parse exchange responses into standardized CandleData objects

## Exchange Families

Based on our analysis of common patterns, exchanges fall into these general families:

| Family | Trading Pairs | Timestamp | WebSocket Format | Response Format | Examples |
|--------|---------------|-----------|------------------|-----------------|----------|
| Binance-Style | No separator | Milliseconds | Method/params | Array-based | Binance, AscendEx |
| Bybit-Style | No separator | Milliseconds | Op/args | Nested objects | Bybit |
| OKX-Style | Slash | Milliseconds | Nested op/args | Data array | OKX |
| Gate.io-Style | Underscore | Seconds | Channel/payload | Array-based | Gate.io |
| Coinbase-Style | Passthrough | ISO format | Custom | Object-based | Coinbase Advanced Trade |

## Using Mixins

### Basic Structure

An adapter using the mixin pattern typically follows this structure:

```python
@ExchangeRegistry.register("exchange_name")
class ExchangeAdapter(
    BaseAdapter,
    SomeTradingPairMixin,
    SomeTimestampMixin,
    SomeWSMixin,
    SomeRESTMixin,
    SomeResponseMixin
):
    """Exchange adapter documentation."""

    def get_rest_url(self) -> str:
        """Return REST API URL."""
        return "https://api.exchange.com"

    def get_ws_url(self) -> str:
        """Return WebSocket URL."""
        return "wss://ws.exchange.com"

    # Additional exchange-specific methods
```

### Mixin Requirements

Some mixins expect other mixins to be present in the adapter:

- **WebSocket Subscription mixins** require a Trading Pair Formatter mixin
- **REST Parameter mixins** require both Trading Pair Formatter and Timestamp Handler mixins
- **Response Parser mixins** require a Timestamp Handler mixin

### Overriding Methods

You can override mixin methods when an exchange has specific behavior that differs from the standard pattern:

```python
def get_channel_name(self) -> str:
    """Return custom channel name for this exchange."""
    return "exchange.candles"
```

## Available Mixins

### Trading Pair Formatters

- `NoSeparatorTradingPairMixin` - For exchanges using "BTCUSDT" format
- `SlashTradingPairMixin` - For exchanges using "BTC/USDT" format
- `UnderscoreTradingPairMixin` - For exchanges using "BTC_USDT" format
- `PassthroughTradingPairMixin` - For exchanges using "BTC-USDT" format (our standard)

### Timestamp Handlers

- `MillisecondTimestampMixin` - For exchanges using millisecond timestamps
- `SecondTimestampMixin` - For exchanges using second timestamps
- `ISOTimestampMixin` - For exchanges using ISO-8601 timestamps
- `UnixTimestampMixin` - Utility mixin with current time methods

### WebSocket Subscription Handlers

- `MethodParamsWSMixin` - For Binance-style exchanges
- `OpArgsWSMixin` - For Bybit/OKX-style exchanges
- `NestedObjectWSMixin` - For OKX-style nested object parameters
- `ChannelPayloadWSMixin` - For Gate.io-style exchanges

### REST Parameter Handlers

- `BinanceStyleRESTMixin` - For Binance-style parameters
- `BybitStyleRESTMixin` - For Bybit-style parameters with category
- `OKXStyleRESTMixin` - For OKX-style parameters with instType
- `CoinbaseStyleRESTMixin` - For Coinbase-style parameters with granularity

### Response Parsers

- `BinanceArrayResponseMixin` - For array-based responses
- `BybitObjectResponseMixin` - For nested object responses
- `OKXObjectResponseMixin` - For OKX-style data arrays
- `CoinbaseObjectResponseMixin` - For object-based responses

## Testing Mixins

Test cases for mixins should verify:

1. Individual mixin behavior
2. Mixin behavior when composed in an adapter
3. Edge cases for the specific exchange formats

See `tests/unit/adapters/mixins/` for examples of mixin tests.

## Examples

### Binance Spot Adapter

```python
@ExchangeRegistry.register("binance_spot")
class BinanceSpotAdapter(
    BaseAdapter,
    NoSeparatorTradingPairMixin,
    MillisecondTimestampMixin,
    MethodParamsWSMixin,
    BinanceStyleRESTMixin,
    BinanceArrayResponseMixin
):
    """Binance spot markets adapter."""

    def get_rest_url(self) -> str:
        return "https://api.binance.com"

    def get_ws_url(self) -> str:
        return "wss://stream.binance.com:9443/ws"
```

### OKX Spot Adapter

```python
@ExchangeRegistry.register("okx_spot")
class OKXSpotAdapter(
    BaseAdapter,
    SlashTradingPairMixin,
    MillisecondTimestampMixin,
    NestedObjectWSMixin,
    OKXStyleRESTMixin,
    OKXObjectResponseMixin
):
    """OKX spot markets adapter."""

    def get_rest_url(self) -> str:
        return "https://www.okx.com"

    def get_ws_url(self) -> str:
        return "wss://ws.okx.com:8443/ws/v5/public"

    def get_inst_type(self) -> str:
        return "SPOT"
```

## Creating a New Exchange Adapter

1. Analyze the exchange API to understand its behavior patterns
2. Choose the appropriate mixins for each aspect of behavior
3. Implement exchange-specific methods and URLs
4. Test the adapter with the exchange's specific formats and responses

For more detailed examples, see `docs/examples/adapter_composition.md`.
