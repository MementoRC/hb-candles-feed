"""
Exchange-specific plugins for the mock exchange server.

These plugins translate between the standardized mock server format
and the exchange-specific formats.
"""

from candles_feed.mocking_resources.exchanges.binance.spot_plugin import BinanceSpotPlugin
from candles_feed.mocking_resources.exchanges.okx.spot_plugin import OKXSpotPlugin
from candles_feed.mocking_resources.exchanges.okx.perpetual_plugin import OKXPerpetualPlugin
from candles_feed.mocking_resources.exchanges.bybit.spot_plugin import BybitSpotPlugin
from candles_feed.mocking_resources.exchanges.bybit.perpetual_plugin import BybitPerpetualPlugin
from candles_feed.mocking_resources.exchanges.coinbase_advanced_trade.spot_plugin import CoinbaseAdvancedTradeSpotPlugin
from candles_feed.mocking_resources.exchanges.kraken.spot_plugin import KrakenSpotPlugin
# from candles_feed.mocking_resources.exchanges.gate_io.spot_plugin import GateIoSpotPlugin
# from candles_feed.mocking_resources.exchanges.hyperliquid.spot_plugin import HyperliquidSpotPlugin
# from candles_feed.mocking_resources.exchanges.kucoin.spot_plugin import KucoinSpotPlugin
# from candles_feed.mocking_resources.exchanges.mexc.spot_plugin import MexcSpotPlugin


__all__ = [
    "BinanceSpotPlugin",
    "OKXSpotPlugin",
    "OKXPerpetualPlugin",
    "BybitSpotPlugin",
    "BybitPerpetualPlugin",
    "CoinbaseAdvancedTradeSpotPlugin",
    "KrakenSpotPlugin",
#     "GateIoSpotPlugin",
#     "HyperliquidSpotPlugin",
#     "KucoinSpotPlugin",
#     "MexcSpotPlugin",
]
