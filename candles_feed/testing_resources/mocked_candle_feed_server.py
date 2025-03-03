"""
Test Exchange Server for end-to-end testing of the Candles Feed.

This module provides a wrapper around the MockExchangeServer that adds URL patching
capabilities, making it easy to use in end-to-end tests.
"""

import importlib
import logging
from typing import Dict, List, Optional, Tuple

from candles_feed.testing_resources.mocks.core.exchange_plugin import ExchangePlugin
from candles_feed.testing_resources.mocks.core.exchange_type import ExchangeType
from candles_feed.testing_resources.mocks.core.server import MockExchangeServer
from candles_feed.testing_resources.mocks.exchanges.binance_spot.plugin import BinanceSpotPlugin

logger = logging.getLogger(__name__)


class MockedCandlesFeedServer:
    """Wrapper for the MockExchangeServer with URL patching capabilities for end-to-end testing."""

    def __init__(self, exchange_type: ExchangeType, host: str = "127.0.0.1", port: int = 8789):
        """Initialize the test exchange server.

        Args:
            exchange_type: Type of exchange to mock
            host: Host to bind the server to
            port: Port to bind the server to
        """
        self.exchange_type = exchange_type
        self.host = host
        self.port = port
        self.server: Optional[MockExchangeServer] = None
        self.url: Optional[str] = None
        self.original_urls: Dict[str, str] = {}

        # Select the appropriate plugin based on exchange type
        self.plugin = self._create_plugin(exchange_type)

        # Create the server
        self.server = MockExchangeServer(self.plugin, host, port)

    def _create_plugin(self, exchange_type: ExchangeType) -> ExchangePlugin:
        """Create the appropriate plugin for the exchange type."""
        if exchange_type == ExchangeType.BINANCE_SPOT:
            return BinanceSpotPlugin(exchange_type)
        elif exchange_type == ExchangeType.BINANCE_PERPETUAL:
            # Currently using BinanceSpotPlugin for BINANCE_PERPETUAL as well
            return BinanceSpotPlugin(exchange_type)
        else:
            # For now, fall back to BinanceSpotPlugin for other exchange types
            # In a complete implementation, we would have specific plugins for each
            logger.warning(
                f"No dedicated plugin for {exchange_type.value}, using BinanceSpotPlugin"
            )
            return BinanceSpotPlugin(exchange_type)

    async def start(self, trading_pairs: List[Tuple[str, str, float]] = None) -> str:
        """Start the test exchange server.

        Args:
            trading_pairs: List of (trading_pair, interval, initial_price) tuples

        Returns:
            Server URL
        """
        if trading_pairs is None:
            # Default trading pairs
            trading_pairs = [
                ("BTCUSDT", "1m", 50000.0),
                ("ETHUSDT", "1m", 3000.0),
                ("SOLUSDT", "1m", 100.0),
            ]

        # Add trading pairs
        for trading_pair, interval, price in trading_pairs:
            self.server.add_trading_pair(trading_pair, interval, price)

        # Start the server
        self.url = await self.server.start()

        # Patch URLs in the adapter module
        self._patch_adapter_urls()

        return self.url

    def set_network_conditions(
        self, latency_ms: int = 0, packet_loss_rate: float = 0.0, error_rate: float = 0.0
    ):
        """Configure network conditions for error simulation.

        Args:
            latency_ms: Artificial latency in milliseconds
            packet_loss_rate: Rate of packet loss (0.0-1.0)
            error_rate: Rate of error responses (0.0-1.0)
        """
        if self.server:
            self.server.set_network_conditions(
                latency_ms=latency_ms, packet_loss_rate=packet_loss_rate, error_rate=error_rate
            )

    async def stop(self) -> None:
        """Stop the test exchange server and restore original URLs."""
        if self.server:
            await self.server.stop()

        # Restore original URLs
        self._restore_adapter_urls()

    def _get_adapter_constants_module(self) -> Tuple[str, Dict[str, str]]:
        """Get the adapter constants module name and URL attributes based on exchange type."""
        exchange_name = self.exchange_type.value

        # Map exchange types to their module paths and URL attributes
        exchange_module_map = {
            "binance_spot": {
                "module": "candles_feed.adapters.binance.constants",
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
            "binance_perpetual": {
                "module": "candles_feed.adapters.binance.constants",
                "rest_attr": "PERPETUAL_REST_URL",
                "ws_attr": "PERPETUAL_WSS_URL",
            },
            "bybit_spot": {
                "module": "candles_feed.adapters.bybit.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
            "bybit_perpetual": {
                "module": "candles_feed.adapters.bybit.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
            "coinbase_advanced_trade": {
                "module": "candles_feed.adapters.coinbase_advanced_trade.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
            "kraken_spot": {
                "module": "candles_feed.adapters.kraken_spot.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
            "kucoin_spot": {
                "module": "candles_feed.adapters.kucoin.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
            "okx_spot": {
                "module": "candles_feed.adapters.okx.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
            "gate_io_spot": {
                "module": "candles_feed.adapters.gate_io.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
            "hyperliquid_spot": {
                "module": "candles_feed.adapters.hyperliquid.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
            "mexc_spot": {
                "module": "candles_feed.adapters.mexc.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
        }

        # Get module info or use default if not found
        exchange_info = exchange_module_map.get(
            exchange_name,
            {
                "module": f"candles_feed.adapters.{exchange_name.replace('_', '_')}.constants",
                "rest_attr": "REST_URL",
                "ws_attr": "WSS_URL",
            },
        )

        return exchange_info["module"], {
            "rest": exchange_info["rest_attr"],
            "ws": exchange_info["ws_attr"],
        }

    def _patch_adapter_urls(self) -> None:
        """Patch the URLs in the adapter module to point to our mock server."""
        try:
            module_name, attrs = self._get_adapter_constants_module()
            module = importlib.import_module(module_name)

            # Save original URLs
            for _, attr_name in attrs.items():
                if hasattr(module, attr_name):
                    self.original_urls[attr_name] = getattr(module, attr_name)

            # Patch REST URL
            rest_attr = attrs.get("rest")
            if hasattr(module, rest_attr):
                base_url = self.url.rstrip("/")
                # For Binance, we need to append the API path
                if self.exchange_type in [
                    ExchangeType.BINANCE_SPOT,
                    ExchangeType.BINANCE_PERPETUAL,
                ]:
                    rest_url = f"{base_url}/api/v3/klines"
                else:
                    rest_url = base_url
                setattr(module, rest_attr, rest_url)
                logger.info(f"Patched {module_name}.{rest_attr} to {rest_url}")

            # Patch WebSocket URL
            ws_attr = attrs.get("ws")
            if hasattr(module, ws_attr):
                ws_url = f"ws://{self.host}:{self.port}/ws"
                setattr(module, ws_attr, ws_url)
                logger.info(f"Patched {module_name}.{ws_attr} to {ws_url}")

        except (ImportError, AttributeError) as e:
            logger.error(f"Error patching adapter URLs: {e}")

    def _restore_adapter_urls(self) -> None:
        """Restore the original URLs in the adapter module."""
        if not self.original_urls:
            return

        try:
            module_name, _ = self._get_adapter_constants_module()
            module = importlib.import_module(module_name)

            # Restore original URLs
            for attr_name, original_url in self.original_urls.items():
                if hasattr(module, attr_name):
                    setattr(module, attr_name, original_url)
                    logger.info(f"Restored {module_name}.{attr_name} to {original_url}")

        except (ImportError, AttributeError) as e:
            logger.error(f"Error restoring adapter URLs: {e}")
