# Adapter Composition with Mixins

This document demonstrates how to create exchange adapters using the mixin composition pattern.

## Overview

The `candles_feed` package uses a mixin-based composition pattern to create exchange adapters. This approach allows for:

1. **Reusability**: Common behaviors are defined once and reused across adapters
2. **Maintainability**: Change behavior in one place, affects all adapters using it
3. **Flexibility**: Easily combine different behaviors to support new exchanges
4. **Clarity**: Self-documenting code makes it clear which behaviors an adapter implements

## Exchange Families

We've identified several exchange families with similar behaviors:

1. **Binance-Style**: Binance Spot/Perpetual, AscendEx (no separator trading pairs, method/params WS format)
2. **Bybit-Style**: Bybit Spot/Perpetual (no separator trading pairs, op/args WS format, category parameter)
3. **OKX-Style**: OKX Spot/Perpetual (slash trading pairs, nested object WS format)
4. **Gate.io-Style**: Gate.io Spot/Perpetual (underscore trading pairs, channel/event/payload WS format)
5. **Coinbase-Style**: Coinbase Advanced Trade (original trading pairs, object-based responses)

## Basic Usage

Here's a simple example of creating a Binance Spot adapter using mixins:

```python
from candles_feed.adapters.base.base_adapter import BaseAdapter
from candles_feed.adapters.mixins import (
    NoSeparatorTradingPairMixin,
    MillisecondTimestampMixin,
    MethodParamsWSMixin,
    BinanceStyleRESTMixin,
    BinanceArrayResponseMixin
)
from candles_feed.core.exchange_registry import ExchangeRegistry

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
        """Return REST API URL for Binance Spot."""
        return "https://api.binance.com"
        
    def get_ws_url(self) -> str:
        """Return WebSocket URL for Binance Spot."""
        return "wss://stream.binance.com:9443/ws"
```

## Implementing Different Exchange Types

### Bybit Perpetual Example

```python
from candles_feed.adapters.base.base_adapter import BaseAdapter
from candles_feed.adapters.mixins import (
    NoSeparatorTradingPairMixin,
    MillisecondTimestampMixin,
    OpArgsWSMixin,
    BybitStyleRESTMixin,
    BybitObjectResponseMixin
)
from candles_feed.core.exchange_registry import ExchangeRegistry

@ExchangeRegistry.register("bybit_perpetual")
class BybitPerpetualAdapter(
    BaseAdapter,
    NoSeparatorTradingPairMixin,
    MillisecondTimestampMixin,
    OpArgsWSMixin,
    BybitStyleRESTMixin,
    BybitObjectResponseMixin
):
    """Bybit perpetual markets adapter."""
    
    def get_rest_url(self) -> str:
        """Return REST API URL for Bybit Perpetual."""
        return "https://api.bybit.com"
        
    def get_ws_url(self) -> str:
        """Return WebSocket URL for Bybit Perpetual."""
        return "wss://stream.bybit.com/v5/public/linear"
        
    def get_category_param(self) -> str:
        """Return category parameter for Bybit Perpetual."""
        return "linear"
```

### OKX Spot Example

```python
from candles_feed.adapters.base.base_adapter import BaseAdapter
from candles_feed.adapters.mixins import (
    SlashTradingPairMixin,
    MillisecondTimestampMixin,
    NestedObjectWSMixin,
    OKXStyleRESTMixin,
    OKXObjectResponseMixin
)
from candles_feed.core.exchange_registry import ExchangeRegistry

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
        """Return REST API URL for OKX Spot."""
        return "https://www.okx.com"
        
    def get_ws_url(self) -> str:
        """Return WebSocket URL for OKX Spot."""
        return "wss://ws.okx.com:8443/ws/v5/public"
        
    def get_inst_type(self) -> str:
        """Return instrument type for OKX Spot."""
        return "SPOT"
```

### Gate.io Spot Example

```python
from candles_feed.adapters.base.base_adapter import BaseAdapter
from candles_feed.adapters.mixins import (
    UnderscoreTradingPairMixin,
    SecondTimestampMixin,
    ChannelPayloadWSMixin,
    BinanceStyleRESTMixin,  # Gate.io uses similar REST params to Binance
    BinanceArrayResponseMixin
)
from candles_feed.core.exchange_registry import ExchangeRegistry

@ExchangeRegistry.register("gate_io_spot")
class GateIoSpotAdapter(
    BaseAdapter,
    UnderscoreTradingPairMixin,
    SecondTimestampMixin,
    ChannelPayloadWSMixin,
    BinanceStyleRESTMixin,
    BinanceArrayResponseMixin
):
    """Gate.io spot markets adapter."""
    
    def get_rest_url(self) -> str:
        """Return REST API URL for Gate.io Spot."""
        return "https://api.gateio.ws"
        
    def get_ws_url(self) -> str:
        """Return WebSocket URL for Gate.io Spot."""
        return "wss://api.gateio.ws/ws/v4/"
        
    def get_channel_name(self) -> str:
        """Return channel name for Gate.io Spot."""
        return "spot.candlesticks"
```

### Coinbase Advanced Trade Example

```python
from candles_feed.adapters.base.base_adapter import BaseAdapter
from candles_feed.adapters.mixins import (
    PassthroughTradingPairMixin,
    ISOTimestampMixin,
    WSSubscriptionMixin,  # Custom implementation needed
    CoinbaseStyleRESTMixin,
    CoinbaseObjectResponseMixin
)
from candles_feed.core.exchange_registry import ExchangeRegistry

@ExchangeRegistry.register("coinbase_advanced_trade")
class CoinbaseAdvancedTradeAdapter(
    BaseAdapter,
    PassthroughTradingPairMixin,
    ISOTimestampMixin,
    CoinbaseStyleRESTMixin,
    CoinbaseObjectResponseMixin
):
    """Coinbase Advanced Trade adapter."""
    
    def get_rest_url(self) -> str:
        """Return REST API URL for Coinbase Advanced Trade."""
        return "https://api.exchange.coinbase.com"
        
    def get_ws_url(self) -> str:
        """Return WebSocket URL for Coinbase Advanced Trade."""
        return "wss://advanced-trade-ws.coinbase.com"
        
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Coinbase has a unique subscription format."""
        return {
            "type": "subscribe",
            "product_ids": [self.get_trading_pair_format(trading_pair)],
            "channels": ["candles"],
            "channel_params": {
                "interval": interval
            }
        }
```

## Creating a New Exchange Adapter

To add support for a new exchange:

1. **Analyze the API**: Determine which trading pair format, timestamp format, etc. it uses
2. **Choose Mixins**: Pick the appropriate mixins based on the exchange's behavior
3. **Implement Specifics**: Add exchange-specific URLs and override any methods as needed
4. **Register**: Register the adapter with the exchange registry

## Testing Your Adapter

Write tests to verify:

1. Trading pair formatting
2. Parameter formatting
3. Response parsing
4. WebSocket subscription handling

Use the provided test fixtures and mock data to make testing easier.

## Mock Server Implementation

For the mock server implementation, follow a similar pattern:

```python
from mocking_resources.core import ExchangePlugin
from mocking_resources.core import ExchangeType
from candles_feed.adapters.mixins import (
    NoSeparatorTradingPairMixin,
    BinanceArrayResponseMixin
)


class BinanceSpotPlugin(ExchangePlugin, NoSeparatorTradingPairMixin):
    """Binance spot mock plugin."""

    def __init__(self, exchange_type: ExchangeType):
        super().__init__(exchange_type)

    # Implement required methods...
```

The mixins help ensure the mock server behaves in the same way as the real adapter.