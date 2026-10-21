"""Tests for CandlesFactory — connector routing."""

import pytest


class TestCandlesFactory:
    """CandlesFactory must match hummingbot's get_candle(config) signature."""

    def test_get_candle_returns_adapter(self):
        from candles_feed.hb_compat.data_types import CandlesConfig
        from candles_feed.hb_compat.factory import CandlesFactory

        config = CandlesConfig(connector="binance", trading_pair="BTC-USDT")
        candle = CandlesFactory.get_candle(config)

        from candles_feed.hb_compat.adapter import CandlesBaseAdapter

        assert isinstance(candle, CandlesBaseAdapter)

    def test_get_candle_passes_config_fields(self):
        from candles_feed.hb_compat.data_types import CandlesConfig
        from candles_feed.hb_compat.factory import CandlesFactory

        config = CandlesConfig(
            connector="binance",
            trading_pair="ETH-USDT",
            interval="5m",
            max_records=1000,
        )
        candle = CandlesFactory.get_candle(config)
        assert candle.name == "binance_spot"  # registry key, not hummingbot name
        assert candle.interval == "5m"
        assert candle.max_records == 1000

    def test_get_candle_without_connector_defaults_to_none(self):
        from candles_feed.hb_compat.data_types import CandlesConfig
        from candles_feed.hb_compat.factory import CandlesFactory

        config = CandlesConfig(connector="binance", trading_pair="BTC-USDT")
        assert not hasattr(CandlesFactory.get_candle(config), "connector")

    def test_get_candle_accepts_connector_kwarg(self):
        """MarketDataProvider calls get_candle(config, connector=...)."""
        from candles_feed.hb_compat.data_types import CandlesConfig
        from candles_feed.hb_compat.factory import CandlesFactory

        config = CandlesConfig(connector="binance", trading_pair="BTC-USDT")
        candle = CandlesFactory.get_candle(config, connector=object())
        assert candle.name == "binance_spot"

    def test_get_candle_accepts_connector_positionally(self):
        from candles_feed.hb_compat.data_types import CandlesConfig
        from candles_feed.hb_compat.factory import CandlesFactory

        config = CandlesConfig(connector="binance", trading_pair="BTC-USDT")
        candle = CandlesFactory.get_candle(config, object())
        assert candle.name == "binance_spot"

    def test_get_candle_screener_volatility_call_shape(self):
        """scripts/screener_volatility.py:49 -- single positional CandlesConfig, no connector."""
        from candles_feed.hb_compat.data_types import CandlesConfig
        from candles_feed.hb_compat.factory import CandlesFactory

        combination = ("ETH-USDT", "3m")
        candle = CandlesFactory.get_candle(
            CandlesConfig(
                connector="binance_perpetual",
                trading_pair=combination[0],
                interval=combination[1],
                max_records=200,
            )
        )
        assert candle.name == "binance_perpetual"
        assert candle.interval == "3m"
        assert candle.max_records == 200
        assert not hasattr(candle, "connector")

    def test_connector_is_not_retained(self):
        import gc
        import weakref

        from candles_feed.hb_compat.data_types import CandlesConfig
        from candles_feed.hb_compat.factory import CandlesFactory

        class FakeConnector:
            pass

        connector = FakeConnector()
        ref = weakref.ref(connector)
        config = CandlesConfig(connector="binance", trading_pair="BTC-USDT")
        candle = CandlesFactory.get_candle(config, connector=connector)
        del connector
        gc.collect()
        assert ref() is None
        assert candle is not None

    def test_unsupported_connector_raises(self):
        from candles_feed.hb_compat.data_types import (
            CandlesConfig,
            UnsupportedConnectorError,
        )
        from candles_feed.hb_compat.factory import CandlesFactory

        config = CandlesConfig(connector="dydx", trading_pair="BTC-USDT")
        with pytest.raises(UnsupportedConnectorError, match="dydx"):
            CandlesFactory.get_candle(config)

    def test_all_supported_connectors(self):
        from candles_feed.hb_compat.factory import CandlesFactory

        supported = CandlesFactory.get_supported_connectors()
        assert "aevo_perpetual" in supported
        assert "ascend_ex" in supported
        assert "binance" in supported
        assert "binance_perpetual" in supported
        assert "bitget" in supported
        assert "bitget_perpetual" in supported
        assert "bitmart_perpetual" in supported
        assert "btc_markets" in supported
        assert "bybit" in supported
        assert "bybit_perpetual" in supported
        assert "coinbase_advanced_trade" in supported
        assert "dexalot" in supported
        assert "gate_io" in supported
        assert "gate_io_perpetual" in supported
        assert "hyperliquid" in supported
        assert "hyperliquid_perpetual" in supported
        assert "kraken" in supported
        assert "kucoin" in supported
        assert "kucoin_perpetual" in supported
        assert "mexc" in supported
        assert "mexc_perpetual" in supported
        assert "okx" in supported
        assert "okx_perpetual" in supported
        assert "pacifica_perpetual" in supported
        assert len(supported) == 24

    def test_get_supported_connectors_returns_copy(self):
        from candles_feed.hb_compat.factory import CandlesFactory

        s1 = CandlesFactory.get_supported_connectors()
        s1.add("fake")
        s2 = CandlesFactory.get_supported_connectors()
        assert "fake" not in s2
