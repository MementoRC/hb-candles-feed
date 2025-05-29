"""
Server factory for creating mock exchange servers.
"""

import importlib
import logging
from typing import List, Optional, Tuple, TypeVar

from candles_feed.mocking_resources.core.exchange_type import ExchangeType

logger = logging.getLogger(__name__)


_PLUGIN_REGISTRY = {}


def register_plugin(exchange_type: ExchangeType, plugin):
    """Register an exchange plugin.

    :param exchange_type: The exchange type
    :param plugin: The plugin instance
    :raises ValueError: If a plugin is already registered for this exchange type
    """
    if exchange_type in _PLUGIN_REGISTRY:
        raise ValueError(f"Plugin already registered for exchange type {exchange_type.value}")

    _PLUGIN_REGISTRY[exchange_type] = plugin


def get_plugin(exchange_type: ExchangeType):
    """Get the plugin for an exchange type.

    :param exchange_type: ExchangeType:
    :returns: The plugin instance, or None if not found
    """
    # Check if we already have a plugin registered
    if exchange_type in _PLUGIN_REGISTRY:
        return _PLUGIN_REGISTRY[exchange_type]

    # Use the comprehensive plugin registry
    return _get_plugin_from_registry(exchange_type)


def _get_plugin_from_registry(exchange_type: ExchangeType):
    """Get a plugin instance using the plugin registry mapping.

    :param exchange_type: The exchange type to get a plugin for
    :returns: A plugin instance or None if no plugin is registered
    """
    # Plugin registry mapping
    PLUGIN_REGISTRY = {
        ExchangeType.BINANCE_SPOT: "candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin.BinanceSpotPlugin",
        ExchangeType.BINANCE_PERPETUAL: "candles_feed.mocking_resources.exchange_server_plugins.binance.perpetual_plugin.BinancePerpetualPlugin",
        ExchangeType.OKX_SPOT: "candles_feed.mocking_resources.exchange_server_plugins.okx.spot_plugin.OKXSpotPlugin",
        ExchangeType.OKX_PERPETUAL: "candles_feed.mocking_resources.exchange_server_plugins.okx.perpetual_plugin.OKXPerpetualPlugin",
        ExchangeType.BYBIT_SPOT: "candles_feed.mocking_resources.exchange_server_plugins.bybit.spot_plugin.BybitSpotPlugin",
        ExchangeType.BYBIT_PERPETUAL: "candles_feed.mocking_resources.exchange_server_plugins.bybit.perpetual_plugin.BybitPerpetualPlugin",
        ExchangeType.COINBASE_ADVANCED_TRADE: "candles_feed.mocking_resources.exchange_server_plugins.coinbase_advanced_trade.spot_plugin.CoinbaseAdvancedTradeSpotPlugin",
        ExchangeType.KRAKEN_SPOT: "candles_feed.mocking_resources.exchange_server_plugins.kraken.spot_plugin.KrakenSpotPlugin",
        ExchangeType.KUCOIN_SPOT: "candles_feed.mocking_resources.exchange_server_plugins.kucoin.spot_plugin.KucoinSpotPlugin",
        ExchangeType.KUCOIN_PERPETUAL: "candles_feed.mocking_resources.exchange_server_plugins.kucoin.perpetual_plugin.KucoinPerpetualPlugin",
        ExchangeType.GATE_IO_SPOT: "candles_feed.mocking_resources.exchange_server_plugins.gate_io.spot_plugin.GateIoSpotPlugin",
        ExchangeType.GATE_IO_PERPETUAL: "candles_feed.mocking_resources.exchange_server_plugins.gate_io.perpetual_plugin.GateIoPerpetualPlugin",
        ExchangeType.MEXC_SPOT: "candles_feed.mocking_resources.exchange_server_plugins.mexc.spot_plugin.MEXCSpotPlugin",
        ExchangeType.MEXC_PERPETUAL: "candles_feed.mocking_resources.exchange_server_plugins.mexc.perpetual_plugin.MEXCPerpetualPlugin",
        ExchangeType.HYPERLIQUID_SPOT: "candles_feed.mocking_resources.exchange_server_plugins.hyperliquid.spot_plugin.HyperliquidSpotPlugin",
        ExchangeType.HYPERLIQUID_PERPETUAL: "candles_feed.mocking_resources.exchange_server_plugins.hyperliquid.perpetual_plugin.HyperliquidPerpetualPlugin",
        ExchangeType.ASCEND_EX_SPOT: "candles_feed.mocking_resources.exchange_server_plugins.ascend_ex.spot_plugin.AscendExSpotPlugin",
    }

    # Check if we have a mapping for this exchange type
    plugin_path = PLUGIN_REGISTRY.get(exchange_type)
    if not plugin_path:
        # Try to dynamically generate a path
        try:
            # Convert exchange_type to a module path
            # e.g., binance_spot -> candles_feed.mocking_resources.exchange_server_plugins.binance.spot_plugin
            module_path = f"candles_feed.mocking_resources.exchange_server_plugins.{exchange_type.value.replace('_', '.')}_plugin"
            module = importlib.import_module(module_path)

            # Get class name from exchange type
            # e.g., binance_spot -> BinanceSpotPlugin
            parts = exchange_type.value.split("_")
            class_name = "".join(part.capitalize() for part in parts) + "Plugin"

            # Get the plugin class
            plugin_class = getattr(module, class_name)

            # Create instance
            plugin = plugin_class()

            # Register for future use
            _PLUGIN_REGISTRY[exchange_type] = plugin

            return plugin
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import plugin for {exchange_type.value}: {e}")
            return None

    # Use the mapping to import and instantiate the plugin
    try:
        module_path, class_name = plugin_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name)
        plugin = plugin_class()

        # Register for future use
        _PLUGIN_REGISTRY[exchange_type] = plugin

        return plugin
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import plugin for {exchange_type.value}: {e}")
        return None


MockExchangeServerT = TypeVar("MockExchangeServerT", bound="MockedExchangeServer")

def create_mock_server(
    exchange_type: ExchangeType,
    host: str = "127.0.0.1",
    port: int = 8080,
    trading_pairs: Optional[List[Tuple[str, str, float]]] = None
) -> Optional[MockExchangeServerT]:
    """Create a mock exchange server.

    :param exchange_type: The type of exchange to mock
    :param host: The host to bind to (Default value = "127.0.0.1")
    :param port: The port to bind to (Default value = 8080)
    :param trading_pairs: Optional list of trading pairs to initialize
                    Each tuple contains (symbol, interval, initial_price) (Default value = None)
    :returns: A configured MockedExchangeServer instance, or None if the plugin
        for the specified exchange type cannot be found
    """
    # Import here to avoid circular imports
    from candles_feed.mocking_resources.core.server import MockedExchangeServer

    logger.info(f"Creating mock server for {exchange_type.value} at {host}:{port}")

    # Get the plugin for this exchange type
    plugin = get_plugin(exchange_type)
    if plugin is None:
        logger.error(f"No plugin found for exchange type {exchange_type.value}")
        return None

    # Create the server instance
    server = MockedExchangeServer(plugin, host, port)

    # Add trading pairs
    if trading_pairs:
        for symbol, interval, price in trading_pairs:
            server.add_trading_pair(symbol, interval, price)
    else:
        # Add some default trading pairs
        server.add_trading_pair("BTC-USDT", "1m", 50000.0)
        server.add_trading_pair("ETH-USDT", "1m", 3000.0)
        server.add_trading_pair("SOL-USDT", "1m", 100.0)

    return server
