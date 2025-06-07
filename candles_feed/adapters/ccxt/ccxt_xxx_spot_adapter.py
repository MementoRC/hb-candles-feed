"""
CCXT Binance spot adapter implementation.

This module provides a concrete implementation of the CCXT adapter for Binance spot.
"""

from candles_feed.adapters.ccxt.ccxt_base_adapter import CCXTBaseAdapter


class CCXTBinanceSpotAdapter(CCXTBaseAdapter):
    """CCXT adapter for Binance spot exchange.

    This adapter uses CCXT to interact with Binance's REST API.
    """

    exchange_name = "binance"
    market_type = "spot"

    # WebSocket-specific methods deliberately not implemented
    # since we use NoWebSocketSupportMixin
