# Mock Exchange Server Sample Code

This document provides sample code for the key components of the proposed mock exchange server implementation.

## 1. MockCandleData

```python
"""
Mock candle data model for testing.
"""

import random
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class MockCandleData:
    """
    Candle data structure for mock exchange data.
    
    This is a standardized representation of candle data used by the mock server.
    Each exchange adapter will convert between this format and their exchange-specific format.
    """
    timestamp: int  # Unix timestamp in seconds
    open: float
    high: float 
    low: float
    close: float
    volume: float
    quote_asset_volume: float
    n_trades: int
    taker_buy_base_volume: float
    taker_buy_quote_volume: float
    
    @property
    def timestamp_ms(self) -> int:
        """Return timestamp in milliseconds."""
        return self.timestamp * 1000
    
    @classmethod
    def create_random(cls, timestamp: int, previous_candle: Optional['MockCandleData'] = None, 
                      base_price: float = 50000.0, volatility: float = 0.01) -> 'MockCandleData':
        """
        Create a random candle, optionally based on a previous candle.
        
        Args:
            timestamp: Unix timestamp in seconds
            previous_candle: Previous candle to base price movements on
            base_price: Base price if no previous candle is provided
            volatility: Price volatility as a decimal percentage (0.01 = 1%)
            
        Returns:
            A new MockCandleData instance with random but realistic values
        """
        if previous_candle:
            # Base the new candle on the previous close price
            base_price = previous_candle.close
        
        # Generate price movement
        price_change = (random.random() - 0.5) * 2 * volatility * base_price
        close_price = base_price + price_change
        
        # Create a realistic OHLC pattern
        price_range = abs(price_change) * 1.5
        open_price = base_price
        high_price = max(open_price, close_price) + (random.random() * price_range * 0.5)
        low_price = min(open_price, close_price) - (random.random() * price_range * 0.5)
        
        # Generate volume data
        volume = 10.0 + (random.random() * 20.0)
        quote_volume = volume * ((open_price + close_price) / 2)
        
        # Taker volume (typically 40-60% of total volume)
        taker_ratio = 0.4 + (random.random() * 0.2)
        taker_base_volume = volume * taker_ratio
        taker_quote_volume = taker_base_volume * ((open_price + close_price) / 2)
        
        # Number of trades - correlates somewhat with volume
        n_trades = int(50 + (volume * 5) + (random.random() * 50))
        
        return cls(
            timestamp=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            quote_asset_volume=quote_volume,
            n_trades=n_trades,
            taker_buy_base_volume=taker_base_volume,
            taker_buy_quote_volume=taker_quote_volume
        )
```

## 2. ExchangePlugin Interface

```python
"""
Exchange plugin interface for the mock exchange server.
"""

import abc
from typing import Any, Dict, List, Tuple

from aiohttp import web

from candles_feed.testing_resources.mocks.core.candle_data import MockCandleData
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType


class ExchangePlugin(abc.ABC):
    """
    Base class for exchange-specific plugins for the mock server.
    
    This abstract class defines the interface that all exchange plugins must implement.
    Each exchange adapter needs a corresponding plugin to translate between the
    standardized mock server format and the exchange-specific formats.
    """
    
    def __init__(self, exchange_type: ExchangeType):
        """
        Initialize the exchange plugin.
        
        Args:
            exchange_type: The type of exchange this plugin handles
        """
        self.exchange_type = exchange_type
    
    @property
    @abc.abstractmethod
    def rest_routes(self) -> Dict[str, Tuple[str, str]]:
        """
        Get the REST API routes for this exchange.
        
        Returns:
            A dictionary mapping URL paths to tuples of (HTTP method, handler name)
            Example: {'/api/v3/klines': ('GET', 'handle_klines')}
        """
        pass
    
    @property
    @abc.abstractmethod
    def ws_routes(self) -> Dict[str, str]:
        """
        Get the WebSocket routes for this exchange.
        
        Returns:
            A dictionary mapping URL paths to handler names
            Example: {'/ws': 'handle_websocket'}
        """
        pass
    
    @abc.abstractmethod
    def format_rest_candles(self, candles: List[MockCandleData], 
                           trading_pair: str, interval: str) -> Any:
        """
        Format candle data as a REST API response for this exchange.
        
        Args:
            candles: List of candle data to format
            trading_pair: The trading pair
            interval: The candle interval
            
        Returns:
            Formatted response as expected from the exchange's REST API
        """
        pass
    
    @abc.abstractmethod
    def format_ws_candle_message(self, candle: MockCandleData, 
                                trading_pair: str, interval: str, 
                                is_final: bool = False) -> Any:
        """
        Format candle data as a WebSocket message for this exchange.
        
        Args:
            candle: Candle data to format
            trading_pair: The trading pair
            interval: The candle interval
            is_final: Whether this is the final update for this candle
            
        Returns:
            Formatted message as expected from the exchange's WebSocket API
        """
        pass
    
    @abc.abstractmethod
    def parse_ws_subscription(self, message: Dict) -> List[Tuple[str, str]]:
        """
        Parse a WebSocket subscription message.
        
        Args:
            message: The subscription message from the client
            
        Returns:
            A list of (trading_pair, interval) tuples that the client wants to subscribe to
        """
        pass
    
    @abc.abstractmethod
    def create_ws_subscription_success(self, message: Dict, 
                                      subscriptions: List[Tuple[str, str]]) -> Dict:
        """
        Create a WebSocket subscription success response.
        
        Args:
            message: The original subscription message
            subscriptions: List of (trading_pair, interval) tuples that were subscribed to
            
        Returns:
            A subscription success response message
        """
        pass
    
    @abc.abstractmethod
    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.
        
        Args:
            trading_pair: The trading pair
            interval: The candle interval
            
        Returns:
            A string key used to track subscriptions
        """
        pass
    
    @abc.abstractmethod
    def parse_rest_candles_params(self, request: web.Request) -> Dict[str, Any]:
        """
        Parse REST API parameters for candle requests.
        
        Args:
            request: The web request
            
        Returns:
            A dictionary with standardized parameter names
            (symbol, interval, start_time, end_time, limit)
        """
        pass
```

## 3. Exchange Type Enum

```python
"""
Exchange type definitions for the mock exchange framework.
"""

from enum import Enum


class ExchangeType(Enum):
    """
    Supported exchange types for mocking.
    
    This enum defines all the exchange types that can be simulated by the mock server.
    Each value corresponds to a specific exchange that has a corresponding adapter
    implementation in the candles feed package.
    """
    BINANCE_SPOT = "binance_spot"
    BINANCE_PERPETUAL = "binance_perpetual" 
    BYBIT_SPOT = "bybit_spot"
    BYBIT_PERPETUAL = "bybit_perpetual"
    COINBASE_ADVANCED_TRADE = "coinbase_advanced_trade"
    KRAKEN_SPOT = "kraken_spot"
    KUCOIN_SPOT = "kucoin_spot"
    KUCOIN_PERPETUAL = "kucoin_perpetual"
    OKX_SPOT = "okx_spot"
    OKX_PERPETUAL = "okx_perpetual"
    GATE_IO_SPOT = "gate_io_spot"
    GATE_IO_PERPETUAL = "gate_io_perpetual"
    MEXC_SPOT = "mexc_spot"
    MEXC_PERPETUAL = "mexc_perpetual"
    HYPERLIQUID_SPOT = "hyperliquid_spot"
    HYPERLIQUID_PERPETUAL = "hyperliquid_perpetual"
    ASCEND_EX_SPOT = "ascend_ex_spot"
```

## 4. Server Factory

```python
"""
Server factory for creating mock exchange servers.
"""

import importlib
import logging
from typing import Dict, List, Optional, Tuple

from candles_feed.testing_resources.mocks.core.exchange_plugin import ExchangePlugin
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType
from candles_feed.testing_resources.mocks.core.server import MockExchangeServer


logger = logging.getLogger(__name__)


_PLUGIN_REGISTRY: Dict[ExchangeType, ExchangePlugin] = {}


def register_plugin(exchange_type: ExchangeType, plugin: ExchangePlugin):
    """
    Register an exchange plugin.
    
    Args:
        exchange_type: The exchange type
        plugin: The plugin instance
        
    Raises:
        ValueError: If a plugin is already registered for this exchange type
    """
    if exchange_type in _PLUGIN_REGISTRY:
        raise ValueError(f"Plugin already registered for exchange type {exchange_type.value}")
    
    _PLUGIN_REGISTRY[exchange_type] = plugin


def get_plugin(exchange_type: ExchangeType) -> Optional[ExchangePlugin]:
    """
    Get the plugin for an exchange type.
    
    Args:
        exchange_type: The exchange type
        
    Returns:
        The plugin instance, or None if not found
    """
    # If the plugin is not registered, try to import it
    if exchange_type not in _PLUGIN_REGISTRY:
        try:
            # Convert exchange type to module path
            # e.g., BINANCE_SPOT -> binance_spot
            module_name = exchange_type.value
            
            # Import the plugin module
            module = importlib.import_module(f"candles_feed.testing_resources.mocks.exchanges.{module_name}")
            
            # Get the plugin class (assumed to be named <Exchange>Plugin)
            # e.g., BinanceSpotPlugin
            class_name = "".join(word.capitalize() for word in module_name.split("_")) + "Plugin"
            plugin_class = getattr(module, class_name)
            
            # Create an instance
            plugin = plugin_class(exchange_type)
            
            # Register it
            _PLUGIN_REGISTRY[exchange_type] = plugin
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import plugin for {exchange_type.value}: {e}")
            return None
    
    return _PLUGIN_REGISTRY.get(exchange_type)


def create_mock_server(
    exchange_type: ExchangeType, 
    host: str = '127.0.0.1', 
    port: int = 8080,
    trading_pairs: Optional[List[Tuple[str, str, float]]] = None
) -> Optional[MockExchangeServer]:
    """
    Create a mock exchange server.
    
    Args:
        exchange_type: The type of exchange to mock
        host: The host to bind to
        port: The port to bind to
        trading_pairs: Optional list of trading pairs to initialize
                    Each tuple contains (symbol, interval, initial_price)
                    
    Returns:
        A configured MockExchangeServer instance, or None if the plugin
        for the specified exchange type cannot be found
    """
    # Get the plugin
    plugin = get_plugin(exchange_type)
    if plugin is None:
        logger.error(f"No plugin found for exchange type {exchange_type.value}")
        return None
    
    # Create the server
    server = MockExchangeServer(plugin, host, port)
    
    # Add trading pairs
    if trading_pairs:
        for symbol, interval, price in trading_pairs:
            server.add_trading_pair(symbol, interval, price)
    else:
        # Add some default trading pairs
        server.add_trading_pair("BTCUSDT", "1m", 50000.0)
        server.add_trading_pair("ETHUSDT", "1m", 3000.0)
        server.add_trading_pair("SOLUSDT", "1m", 100.0)
    
    return server
```

## 5. Binance Spot Plugin Example

```python
"""
Binance Spot plugin implementation for the mock exchange server.
"""

import time
from typing import Any, Dict, List, Tuple

from aiohttp import web

from candles_feed.testing_resources.mocks.core.candle_data import MockCandleData
from candles_feed.testing_resources.mocks.core.exchange_plugin import ExchangePlugin
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType


class BinanceSpotPlugin(ExchangePlugin):
    """
    Binance Spot plugin for the mock exchange server.
    
    This plugin implements the Binance Spot API for the mock server,
    translating between the standardized mock server format and the
    Binance-specific formats.
    """
    
    def __init__(self, exchange_type: ExchangeType):
        """
        Initialize the Binance Spot plugin.
        
        Args:
            exchange_type: The exchange type (should be ExchangeType.BINANCE_SPOT)
        """
        super().__init__(exchange_type)
    
    @property
    def rest_routes(self) -> Dict[str, Tuple[str, str]]:
        """
        Get the REST API routes for Binance Spot.
        
        Returns:
            A dictionary mapping URL paths to tuples of (HTTP method, handler name)
        """
        return {
            '/api/v3/ping': ('GET', 'handle_ping'),
            '/api/v3/time': ('GET', 'handle_time'),
            '/api/v3/klines': ('GET', 'handle_klines'),
            '/api/v3/exchangeInfo': ('GET', 'handle_exchange_info')
        }
    
    @property
    def ws_routes(self) -> Dict[str, str]:
        """
        Get the WebSocket routes for Binance Spot.
        
        Returns:
            A dictionary mapping URL paths to handler names
        """
        return {
            '/ws': 'handle_websocket'
        }
    
    def format_rest_candles(self, candles: List[MockCandleData], 
                           trading_pair: str, interval: str) -> List[List]:
        """
        Format candle data as a Binance REST API response.
        
        Args:
            candles: List of candle data to format
            trading_pair: The trading pair
            interval: The candle interval
            
        Returns:
            Formatted response as expected from Binance's REST API
        """
        interval_seconds = self._interval_to_seconds(interval)
        
        return [
            [
                c.timestamp_ms,               # Open time
                str(c.open),                  # Open
                str(c.high),                  # High
                str(c.low),                   # Low
                str(c.close),                 # Close
                str(c.volume),                # Volume
                c.timestamp_ms + (interval_seconds * 1000),  # Close time
                str(c.quote_asset_volume),    # Quote asset volume
                c.n_trades,                   # Number of trades
                str(c.taker_buy_base_volume), # Taker buy base asset volume
                str(c.taker_buy_quote_volume),# Taker buy quote asset volume
                "0"                           # Unused field
            ]
            for c in candles
        ]
    
    def format_ws_candle_message(self, candle: MockCandleData, 
                                trading_pair: str, interval: str, 
                                is_final: bool = False) -> Dict:
        """
        Format candle data as a Binance WebSocket message.
        
        Args:
            candle: Candle data to format
            trading_pair: The trading pair
            interval: The candle interval
            is_final: Whether this is the final update for this candle
            
        Returns:
            Formatted message as expected from Binance's WebSocket API
        """
        interval_seconds = self._interval_to_seconds(interval)
        
        return {
            "e": "kline",                          # Event type
            "E": int(time.time() * 1000),          # Event time
            "s": trading_pair,                     # Symbol
            "k": {
                "t": candle.timestamp_ms,          # Kline start time
                "T": candle.timestamp_ms + (interval_seconds * 1000),  # Kline close time
                "s": trading_pair,                 # Symbol
                "i": interval,                     # Interval
                "f": 100000000,                    # First trade ID
                "L": 100000100,                    # Last trade ID
                "o": str(candle.open),             # Open price
                "c": str(candle.close),            # Close price
                "h": str(candle.high),             # High price
                "l": str(candle.low),              # Low price
                "v": str(candle.volume),           # Base asset volume
                "n": candle.n_trades,              # Number of trades
                "x": is_final,                     # Is this kline closed?
                "q": str(candle.quote_asset_volume),  # Quote asset volume
                "V": str(candle.taker_buy_base_volume),  # Taker buy base asset volume
                "Q": str(candle.taker_buy_quote_volume)  # Taker buy quote asset volume
            }
        }
    
    def parse_ws_subscription(self, message: Dict) -> List[Tuple[str, str]]:
        """
        Parse a Binance WebSocket subscription message.
        
        Args:
            message: The subscription message from the client
            
        Returns:
            A list of (trading_pair, interval) tuples that the client wants to subscribe to
        """
        subscriptions = []
        
        if message.get('method') == 'SUBSCRIBE':
            params = message.get('params', [])
            
            for channel in params:
                # Parse channel (format: symbol@kline_interval)
                parts = channel.split('@')
                if len(parts) != 2 or not parts[1].startswith('kline_'):
                    continue
                
                symbol = parts[0].upper()
                interval = parts[1][6:]  # Remove 'kline_' prefix
                
                subscriptions.append((symbol, interval))
        
        return subscriptions
    
    def create_ws_subscription_success(self, message: Dict, 
                                      subscriptions: List[Tuple[str, str]]) -> Dict:
        """
        Create a Binance WebSocket subscription success response.
        
        Args:
            message: The original subscription message
            subscriptions: List of (trading_pair, interval) tuples that were subscribed to
            
        Returns:
            A subscription success response message
        """
        return {
            "result": None,
            "id": message.get('id', 1)
        }
    
    def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
        """
        Create a WebSocket subscription key for internal tracking.
        
        Args:
            trading_pair: The trading pair
            interval: The candle interval
            
        Returns:
            A string key used to track subscriptions
        """
        return f"{trading_pair.lower()}@kline_{interval}"
    
    def parse_rest_candles_params(self, request: web.Request) -> Dict[str, Any]:
        """
        Parse REST API parameters for Binance candle requests.
        
        Args:
            request: The web request
            
        Returns:
            A dictionary with standardized parameter names
        """
        params = request.query
        
        return {
            'symbol': params.get('symbol'),
            'interval': params.get('interval'),
            'start_time': params.get('startTime'),
            'end_time': params.get('endTime'),
            'limit': params.get('limit', '500')
        }
    
    @staticmethod
    def _interval_to_seconds(interval: str) -> int:
        """Convert interval string to seconds."""
        unit = interval[-1]
        value = int(interval[:-1])
        
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 60 * 60
        elif unit == 'd':
            return value * 24 * 60 * 60
        elif unit == 'w':
            return value * 7 * 24 * 60 * 60
        elif unit == 'M':
            return value * 30 * 24 * 60 * 60
        else:
            raise ValueError(f"Unknown interval unit: {unit}")
```

## 6. Example Usage

```python
"""
Example of using the mock Binance Spot exchange server.
"""

import asyncio
import logging

from candles_feed.testing_resources.mocks import ExchangeType, create_mock_server


async def main():
    """Run a simple example of the mock Binance Spot exchange server."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create a mock Binance Spot server
    server = create_mock_server(
        exchange_type=ExchangeType.BINANCE_SPOT,
        host='127.0.0.1',
        port=8080,
        trading_pairs=[
            ("BTCUSDT", "1m", 50000.0),
            ("ETHUSDT", "1m", 3000.0),
            ("SOLUSDT", "1m", 100.0)
        ]
    )
    
    if server is None:
        logging.error("Failed to create mock server")
        return
    
    # Configure network conditions (optional)
    server.set_network_conditions(
        latency_ms=50,           # 50ms latency
        packet_loss_rate=0.01,   # 1% packet loss
        error_rate=0.005         # 0.5% error rate
    )
    
    # Start the server
    url = await server.start()
    logging.info(f"Mock Binance Spot server started at {url}")
    
    try:
        # Keep the server running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping server...")
    finally:
        # Stop the server
        await server.stop()
        logging.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
```