"""CandlesFactory — drop-in replacement for hummingbot's CandlesFactory.

Maps hummingbot connector names to CandlesBaseAdapter instances. Handles the
name mapping between hummingbot names (e.g., "binance") and ExchangeRegistry
keys (e.g., "binance_spot").
"""

from candles_feed.hb_compat.adapter import CandlesBaseAdapter
from candles_feed.hb_compat.data_types import CandlesConfig, UnsupportedConnectorException


class CandlesFactory:
    """Factory creating CandlesBaseAdapter instances from CandlesConfig.

    Intentionally hardcoded mapping — only explicitly tested exchanges are exposed.
    When new adapters are added and validated, add them to _CONNECTOR_MAP.
    """

    # Maps hummingbot connector names → ExchangeRegistry keys.
    # Hummingbot uses "binance" for spot; registry uses "binance_spot".
    # Perpetual names match directly (e.g., "binance_perpetual").
    _CONNECTOR_MAP: dict[str, str] = {
        "binance": "binance_spot",
        "binance_perpetual": "binance_perpetual",
        "bybit": "bybit_spot",
        "coinbase_advanced_trade": "coinbase_advanced_trade",
        "kraken": "kraken_spot",
        "kucoin": "kucoin_spot",
        "okx": "okx_spot",
    }

    @classmethod
    def get_candle(cls, candles_config: CandlesConfig) -> CandlesBaseAdapter:
        """Create a candle feed adapter from config.

        :param candles_config: Configuration matching hummingbot's CandlesConfig
        :return: CandlesBaseAdapter instance
        :raises UnsupportedConnectorException: If connector is not supported
        """
        registry_key = cls._CONNECTOR_MAP.get(candles_config.connector)
        if registry_key is None:
            raise UnsupportedConnectorException(candles_config.connector)
        return CandlesBaseAdapter(
            exchange=registry_key,
            trading_pair=candles_config.trading_pair,
            interval=candles_config.interval,
            max_records=candles_config.max_records,
        )

    @classmethod
    def get_supported_connectors(cls) -> set[str]:
        """Return set of supported hummingbot connector names.

        :return: Copy of supported connectors set (hummingbot names, not registry keys)
        """
        return set(cls._CONNECTOR_MAP.keys())
