"""
URL patching utility for exchange testing.
"""

import importlib
import logging

from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType

logger = logging.getLogger(__name__)


class ExchangeURLPatcher:
    """
    Utility for patching exchange URLs during testing.

    This class provides functionality to patch URLs in adapter modules to
    point to a mock server, and then restore the original URLs after testing.
    It separates this concern from the server logic.
    """

    def __init__(self, exchange_type: ExchangeType, host: str, port: int):
        """
        Initialize the URL patcher.

        :param exchange_type: Type of exchange to patch URLs for.
        :param host: Host address of the mock server.
        :param port: Port number of the mock server.
        """
        self.exchange_type = exchange_type
        self.host = host
        self.port = port
        self.original_urls: dict[str, dict[str, str]] = {}

    def patch_urls(self, plugin: ExchangePlugin) -> bool:
        """
        Patch URLs for the given plugin to point to the mock server.

        :param plugin: The exchange plugin to patch URLs for.
        :returns: True if patching was successful, False otherwise.
        """
        try:
            # Get module info based on exchange type
            module_info = self._get_adapter_constants_module()
            if not module_info:
                logger.error(f"No module info found for exchange type {self.exchange_type.value}")
                return False

            module_name, attrs = module_info

            # Import the module
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                logger.error(f"Failed to import module {module_name}: {e}")
                return False

            # Save original URLs
            self.original_urls[module_name] = {}
            for _url_type, attr_name in attrs.items():
                if hasattr(module, attr_name):
                    self.original_urls[module_name][attr_name] = getattr(module, attr_name)

            # Get patched URLs from the plugin
            patched_urls = plugin.get_patched_urls(self.host, self.port)

            # Patch REST URL
            rest_attr = attrs.get("rest")
            if rest_attr and hasattr(module, rest_attr):
                rest_url = patched_urls.get("rest", f"http://{self.host}:{self.port}")
                setattr(module, rest_attr, rest_url)
                logger.info(f"Patched {module_name}.{rest_attr} to {rest_url}")

            # Patch WebSocket URL
            ws_attr = attrs.get("ws")
            if ws_attr and hasattr(module, ws_attr):
                ws_url = patched_urls.get("ws", f"ws://{self.host}:{self.port}/ws")
                setattr(module, ws_attr, ws_url)
                logger.info(f"Patched {module_name}.{ws_attr} to {ws_url}")

            return True
        except Exception as e:
            logger.error(f"Error patching URLs: {e}")
            return False

    def restore_urls(self) -> bool:
        """
        Restore original URLs that were patched.

        :returns: True if restoration was successful, False otherwise.
        """
        if not self.original_urls:
            logger.info("No URLs to restore")
            return True

        try:
            for module_name, attrs in self.original_urls.items():
                try:
                    module = importlib.import_module(module_name)

                    for attr_name, original_url in attrs.items():
                        if hasattr(module, attr_name):
                            setattr(module, attr_name, original_url)
                            logger.info(f"Restored {module_name}.{attr_name} to {original_url}")
                except ImportError as e:
                    logger.error(
                        f"Failed to import module {module_name} during URL restoration: {e}"
                    )

            # Clear the stored URLs
            self.original_urls = {}
            return True
        except Exception as e:
            logger.error(f"Error restoring URLs: {e}")
            return False

    def _get_adapter_constants_module(self) -> tuple[str, dict[str, str]] | None:
        """
        Get the adapter constants module name and URL attributes based on exchange type.

        :returns: A tuple containing the module name and a dictionary of URL attributes,
                 or None if no mapping exists for this exchange type.
        """
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
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
            "bybit_perpetual": {
                "module": "candles_feed.adapters.bybit.constants",
                "rest_attr": "PERPETUAL_REST_URL",
                "ws_attr": "PERPETUAL_WSS_URL",
            },
            "coinbase_advanced_trade": {
                "module": "candles_feed.adapters.coinbase_advanced_trade.constants",
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
            "kraken_spot": {
                "module": "candles_feed.adapters.kraken.constants",
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
            "kucoin_spot": {
                "module": "candles_feed.adapters.kucoin.constants",
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
            "kucoin_perpetual": {
                "module": "candles_feed.adapters.kucoin.constants",
                "rest_attr": "PERPETUAL_REST_URL",
                "ws_attr": "PERPETUAL_WSS_URL",
            },
            "okx_spot": {
                "module": "candles_feed.adapters.okx.constants",
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
            "okx_perpetual": {
                "module": "candles_feed.adapters.okx.constants",
                "rest_attr": "PERPETUAL_REST_URL",
                "ws_attr": "PERPETUAL_WSS_URL",
            },
            "gate_io_spot": {
                "module": "candles_feed.adapters.gate_io.constants",
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
            "gate_io_perpetual": {
                "module": "candles_feed.adapters.gate_io.constants",
                "rest_attr": "PERPETUAL_REST_URL",
                "ws_attr": "PERPETUAL_WSS_URL",
            },
            "hyperliquid_spot": {
                "module": "candles_feed.adapters.hyperliquid.constants",
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
            "hyperliquid_perpetual": {
                "module": "candles_feed.adapters.hyperliquid.constants",
                "rest_attr": "PERPETUAL_REST_URL",
                "ws_attr": "PERPETUAL_WSS_URL",
            },
            "mexc_spot": {
                "module": "candles_feed.adapters.mexc.constants",
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
            "mexc_perpetual": {
                "module": "candles_feed.adapters.mexc.constants",
                "rest_attr": "PERPETUAL_REST_URL",
                "ws_attr": "PERPETUAL_WSS_URL",
            },
            "ascend_ex_spot": {
                "module": "candles_feed.adapters.ascend_ex.constants",
                "rest_attr": "SPOT_REST_URL",
                "ws_attr": "SPOT_WSS_URL",
            },
        }

        # Get module info
        exchange_info = exchange_module_map.get(exchange_name)
        if not exchange_info:
            # Try to construct a generic path if specific mapping not found
            is_perpetual = "perpetual" in exchange_name
            exchange_base_name = exchange_name.split("_")[0]

            # Construct a generic module path
            return (
                f"candles_feed.adapters.{exchange_base_name}.constants",
                {
                    "rest": "PERPETUAL_REST_URL" if is_perpetual else "SPOT_REST_URL",
                    "ws": "PERPETUAL_WSS_URL" if is_perpetual else "SPOT_WSS_URL",
                },
            )

        return exchange_info["module"], {
            "rest": exchange_info["rest_attr"],
            "ws": exchange_info["ws_attr"],
        }
