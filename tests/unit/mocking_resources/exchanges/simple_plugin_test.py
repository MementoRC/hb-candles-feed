"""
A simpler test for our plugin implementations.
"""

import pytest

from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType

# Import newly implemented plugins
from candles_feed.mocking_resources.exchanges.binance.perpetual_plugin import BinancePerpetualPlugin
from candles_feed.mocking_resources.exchanges.gate_io.spot_plugin import GateIoSpotPlugin
from candles_feed.mocking_resources.exchanges.gate_io.perpetual_plugin import GateIoPerpetualPlugin
from candles_feed.mocking_resources.exchanges.hyperliquid.spot_plugin import HyperliquidSpotPlugin
from candles_feed.mocking_resources.exchanges.hyperliquid.perpetual_plugin import HyperliquidPerpetualPlugin
from candles_feed.mocking_resources.exchanges.kucoin.spot_plugin import KucoinSpotPlugin
from candles_feed.mocking_resources.exchanges.kucoin.perpetual_plugin import KucoinPerpetualPlugin
from candles_feed.mocking_resources.exchanges.mexc.spot_plugin import MEXCSpotPlugin
from candles_feed.mocking_resources.exchanges.mexc.perpetual_plugin import MEXCPerpetualPlugin


def test_plugin_instantiation():
    """Test that all plugin classes can be instantiated."""
    # Get all plugin classes
    plugin_classes = [
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
        assert hasattr(plugin_instance, "format_rest_candles")
        assert hasattr(plugin_instance, "format_ws_candle_message")
        assert hasattr(plugin_instance, "parse_ws_subscription")
        assert hasattr(plugin_instance, "create_ws_subscription_success")
        assert hasattr(plugin_instance, "create_ws_subscription_key")
        assert hasattr(plugin_instance, "parse_rest_candles_params")