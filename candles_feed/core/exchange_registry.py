"""
Exchange registry for the Candle Feed V2 framework.

This module provides a registry for exchange adapters, allowing for
dynamic discovery and registration of adapters.
"""

import importlib
import logging
import os
import pkgutil
from typing import Dict, List, Optional, Type

from candles_feed.core.protocols import CandleDataAdapter, Logger


class ExchangeRegistry:
    """Registry for exchange adapters with auto-discovery."""

    # Use both _adapters (new API) and _registry (old API) for compatibility
    _adapters: dict[str, type[CandleDataAdapter]] = {}
    _registry: dict[str, type[CandleDataAdapter]] = {}
    _logger: Logger | None = None

    @classmethod
    def logger(cls) -> Logger:
        """Get the logger.

        :return: Logger instance
        """
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    @classmethod
    def register(cls, name: str):
        """Decorator for registering exchange adapters.

        :param name: Adapter name
        :return: Decorator function
        """

        def decorator(adapter_class: type[CandleDataAdapter]):
            cls.logger().info(f"Registering adapter: {name}")
            # Register in both collections for compatibility
            cls._adapters[name] = adapter_class
            cls._registry[name] = adapter_class
            return adapter_class

        return decorator

    @classmethod
    def get_adapter_class(cls, name: str) -> type[CandleDataAdapter]:
        """Get adapter class by name.

        :param name: Adapter name
        :return: Adapter class
        :raises ValueError: If no adapter is registered with the given name
        """
        adapter_class = cls._registry.get(name)
        if adapter_class is None:
            raise ValueError(f"Adapter not found for exchange: {name}")
        return adapter_class

    @classmethod
    def get_adapter(cls, name: str) -> CandleDataAdapter:
        """Get adapter instance by name.

        :param name: Adapter name
        :return: Adapter instance
        :raises ValueError: If no adapter is registered with the given name
        """
        adapter_class = cls.get_adapter_class(name)
        cls.logger().debug(f"Creating adapter instance: {name}")
        return adapter_class()

    @classmethod
    def get_adapter_instance(cls, name: str, *args, **kwargs) -> CandleDataAdapter:
        """Get adapter instance by name with custom args.

        :param name: Adapter name
        :param args: Positional arguments to pass to the adapter constructor
        :param kwargs: Keyword arguments to pass to the adapter constructor
        :return: Adapter instance
        :raises ValueError: If no adapter is registered with the given name
        """
        adapter_class = cls.get_adapter_class(name)
        cls.logger().debug(f"Creating adapter instance with args: {name}")
        return adapter_class(*args, **kwargs)

    @classmethod
    def get_registered_exchanges(cls) -> list[str]:
        """Get list of registered exchange names.

        Returns:
            List of registered exchange names
        """
        return list(cls._registry.keys())

    @classmethod
    def discover_adapters(cls, package_path: str | None = None) -> None:
        """Discover and register adapters in the given package.

        Args:
            package_path: Path to package to search for adapters
        """
        if package_path is None:
            # Default to candles_feed adapters directory
            package_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "adapters")
            )

        cls.logger().info(f"Discovering adapters in: {package_path}")

        # Import all modules in the package to trigger decorator registration
        import_path = os.path.basename(os.path.dirname(package_path))
        if import_path:
            import_path = f"{import_path}."
        import_path += os.path.basename(package_path)

        for _, name, is_pkg in pkgutil.iter_modules([package_path]):
            if is_pkg:
                # This is a potential exchange adapter package
                try:
                    cls.logger().debug(f"Importing potential adapter: {import_path}.{name}")
                    importlib.import_module(f"{import_path}.{name}")
                except ImportError as e:
                    cls.logger().error(f"Error importing {name}: {e}")

    @classmethod
    def list_available_adapters(cls) -> list[str]:
        """List all registered adapter names.

        Returns:
            List of adapter names
        """
        return list(cls._adapters.keys())

    @classmethod
    def list_available_markets(cls) -> dict[str, list[str]]:
        """List all available markets by adapter.

        Returns:
            Dictionary mapping adapter names to list of supported trading pairs
        """
        result = {}
        for name, adapter_class in cls._adapters.items():
            try:
                adapter = adapter_class()
                # Some adapters may implement a get_available_markets method
                if hasattr(adapter, "get_available_markets"):
                    result[name] = adapter.get_available_markets()
                else:
                    result[name] = []
            except Exception as e:
                cls.logger().error(f"Error getting markets for {name}: {e}")
                result[name] = []

        return result
