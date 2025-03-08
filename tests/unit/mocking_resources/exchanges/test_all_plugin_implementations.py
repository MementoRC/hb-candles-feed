"""
Tests for our newly implemented plugin implementations to ensure they can be instantiated properly.
This test serves as a regression test to make sure all plugins remain importable and functional.
"""

from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType
from candles_feed.mocking_resources.exchanges.binance.perpetual_plugin import BinancePerpetualPlugin
from candles_feed.mocking_resources.exchanges.binance.spot_plugin import BinanceSpotPlugin
from candles_feed.mocking_resources.exchanges.gate_io.perpetual_plugin import GateIoPerpetualPlugin
from candles_feed.mocking_resources.exchanges.gate_io.spot_plugin import GateIoSpotPlugin
from candles_feed.mocking_resources.exchanges.hyperliquid.perpetual_plugin import HyperliquidPerpetualPlugin
from candles_feed.mocking_resources.exchanges.hyperliquid.spot_plugin import HyperliquidSpotPlugin
from candles_feed.mocking_resources.exchanges.kucoin.perpetual_plugin import KucoinPerpetualPlugin
from candles_feed.mocking_resources.exchanges.kucoin.spot_plugin import KucoinSpotPlugin
from candles_feed.mocking_resources.exchanges.mexc.perpetual_plugin import MEXCPerpetualPlugin
from candles_feed.mocking_resources.exchanges.mexc.spot_plugin import MEXCSpotPlugin


class TestAllPluginImplementations:
    """
    Test all plugin implementations to make sure they can be instantiated.
    This serves as a regression test to catch any issues with plugin imports or required methods.
    """

    def test_all_plugins_instantiate(self):
        """Test that all plugin classes can be instantiated."""
        # Get all plugin classes from this module
        plugin_classes = [
            BinanceSpotPlugin,
            BinancePerpetualPlugin,
            GateIoSpotPlugin,
            GateIoPerpetualPlugin,
            HyperliquidSpotPlugin,
            HyperliquidPerpetualPlugin,
            KucoinSpotPlugin,
            KucoinPerpetualPlugin,
            MEXCSpotPlugin,
            MEXCPerpetualPlugin,
        ]
        
        # Try to instantiate each plugin
        for plugin_class in plugin_classes:
            plugin_instance = plugin_class()
            
            # Verify this is a valid plugin
            assert isinstance(plugin_instance, ExchangePlugin)
            assert isinstance(plugin_instance.exchange_type, ExchangeType)
            
            # Verify required properties exist
            assert hasattr(plugin_instance, "rest_url")
            assert hasattr(plugin_instance, "wss_url")
            assert hasattr(plugin_instance, "rest_routes")
            assert hasattr(plugin_instance, "ws_routes")
            
            # Verify required methods exist
            assert callable(plugin_instance.format_rest_candles)
            assert callable(plugin_instance.format_ws_candle_message)
            assert callable(plugin_instance.parse_ws_subscription)
            assert callable(plugin_instance.create_ws_subscription_success)
            assert callable(plugin_instance.create_ws_subscription_key)
            assert callable(plugin_instance.parse_rest_candles_params)

    def test_all_exchange_types_covered(self):
        """Test that all exchange types have corresponding plugin implementations."""
        # Get all plugin classes from this module
        plugin_classes = [
            BinanceSpotPlugin,
            BinancePerpetualPlugin,
            GateIoSpotPlugin,
            GateIoPerpetualPlugin,
            HyperliquidSpotPlugin,
            HyperliquidPerpetualPlugin,
            KucoinSpotPlugin,
            KucoinPerpetualPlugin,
            MEXCSpotPlugin,
            MEXCPerpetualPlugin,
        ]
        
        # Instantiate all plugins and collect their exchange types
        exchange_types = [plugin_class().exchange_type for plugin_class in plugin_classes]
        
        # Check only the exchange types we've implemented
        target_exchange_types = [
            ExchangeType.BINANCE_SPOT,
            ExchangeType.BINANCE_PERPETUAL,
            ExchangeType.GATE_IO_SPOT,
            ExchangeType.GATE_IO_PERPETUAL,
            ExchangeType.HYPERLIQUID_SPOT,
            ExchangeType.HYPERLIQUID_PERPETUAL,
            ExchangeType.KUCOIN_SPOT,
            ExchangeType.KUCOIN_PERPETUAL,
            ExchangeType.MEXC_SPOT,
            ExchangeType.MEXC_PERPETUAL,
        ]
        
        for exchange_type in target_exchange_types:
            assert exchange_type in exchange_types, f"No plugin implementation for {exchange_type.name}"