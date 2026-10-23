"""CandlesFactory — drop-in replacement for hummingbot's CandlesFactory.

Maps hummingbot connector names to CandlesBaseAdapter instances. Handles the
name mapping between hummingbot names (e.g., "binance") and ExchangeRegistry
keys (e.g., "binance_spot").
"""

from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.adapter import CandlesBaseAdapter
from candles_feed.hb_compat.data_types import (
    CandlesConfig,
    UnsupportedConnectorError,
    UnsupportedConnectorException,  # noqa: F401  (re-exported, mirrors upstream candles_factory)
)
from candles_feed.hb_compat.throttler_bridge import ConnectorThrottlerBridge


class CandlesFactory:
    """Factory creating CandlesBaseAdapter instances from CandlesConfig.

    Intentionally hardcoded mapping — only explicitly tested exchanges are exposed.
    When new adapters are added and validated, add them to _CONNECTOR_MAP.
    """

    # Maps hummingbot connector names → ExchangeRegistry keys.
    # Hummingbot uses "binance" for spot; registry uses "binance_spot".
    # Perpetual names match directly (e.g., "binance_perpetual").
    _CONNECTOR_MAP: dict[str, str] = {
        "aevo_perpetual": "aevo_perpetual",
        "ascend_ex": "ascend_ex_spot",
        "backpack": "backpack_spot",
        "backpack_perpetual": "backpack_perpetual",
        "binance": "binance_spot",
        "binance_perpetual": "binance_perpetual",
        "bitget": "bitget_spot",
        "bitget_perpetual": "bitget_perpetual",
        "bitmart_perpetual": "bitmart_perpetual",
        "btc_markets": "btc_markets_spot",
        "bybit": "bybit_spot",
        "bybit_perpetual": "bybit_perpetual",
        "coinbase_advanced_trade": "coinbase_advanced_trade",
        "decibel_perpetual": "decibel_perpetual",
        "dexalot": "dexalot_spot",
        "evedex_perpetual": "evedex_perpetual",
        "gate_io": "gate_io_spot",
        "gate_io_perpetual": "gate_io_perpetual",
        "grvt_perpetual": "grvt_perpetual",
        "hyperliquid": "hyperliquid_spot",
        "hyperliquid_perpetual": "hyperliquid_perpetual",
        "kraken": "kraken_spot",
        "kucoin": "kucoin_spot",
        "kucoin_perpetual": "kucoin_perpetual",
        "lighter": "lighter_spot",
        "lighter_perpetual": "lighter_perpetual",
        "mexc": "mexc_spot",
        "mexc_perpetual": "mexc_perpetual",
        "okx": "okx_spot",
        "okx_perpetual": "okx_perpetual",
        "pacifica_perpetual": "pacifica_perpetual",
    }

    @classmethod
    def get_candle(
        cls, candles_config: CandlesConfig, connector: object | None = None
    ) -> CandlesBaseAdapter:
        """Create a candle feed adapter from config.

        :param candles_config: Configuration matching hummingbot's CandlesConfig
        :param connector: Optional host connector. When it exposes a ``throttler``, the
            feed's REST requests draw from that throttler's budget (see
            ``ConnectorThrottlerBridge``); the connector itself is not retained.
        :return: CandlesBaseAdapter instance
        :raises UnsupportedConnectorError: If connector is not supported
        """
        registry_key = cls._CONNECTOR_MAP.get(candles_config.connector)
        if registry_key is None:
            raise UnsupportedConnectorError(candles_config.connector)
        rate_limiter = None
        if connector is not None:
            rate_limiter = cls._bridge_for(connector, registry_key)
        return CandlesBaseAdapter(
            exchange=registry_key,
            trading_pair=candles_config.trading_pair,
            interval=candles_config.interval,
            max_records=candles_config.max_records,
            rate_limiter=rate_limiter,
        )

    @staticmethod
    def _bridge_for(connector: object, registry_key: str) -> ConnectorThrottlerBridge | None:
        """Build the throttler bridge for a connector, or None if it cannot share a budget."""
        adapter_class = ExchangeRegistry.get_adapter_class(registry_key)
        return ConnectorThrottlerBridge.from_connector(connector, adapter_class)

    @classmethod
    def get_supported_connectors(cls) -> set[str]:
        """Return set of supported hummingbot connector names.

        :return: Copy of supported connectors set (hummingbot names, not registry keys)
        """
        return set(cls._CONNECTOR_MAP.keys())
