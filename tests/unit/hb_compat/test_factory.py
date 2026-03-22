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
        assert "binance" in supported
        assert "binance_perpetual" in supported
        assert "bybit" in supported
        assert "coinbase_advanced_trade" in supported
        assert "kraken" in supported
        assert "kucoin" in supported
        assert "okx" in supported
        assert len(supported) == 7

    def test_get_supported_connectors_returns_copy(self):
        from candles_feed.hb_compat.factory import CandlesFactory

        s1 = CandlesFactory.get_supported_connectors()
        s1.add("fake")
        s2 = CandlesFactory.get_supported_connectors()
        assert "fake" not in s2
