"""Tests for hb_compat data types matching hummingbot's interface."""

import pytest
from pydantic import ValidationError


class TestCandlesConfig:
    """CandlesConfig must match hummingbot's field names, types, and defaults."""

    def test_required_fields(self):
        from candles_feed.hb_compat.data_types import CandlesConfig
        config = CandlesConfig(connector="binance", trading_pair="BTC-USDT")
        assert config.connector == "binance"
        assert config.trading_pair == "BTC-USDT"

    def test_defaults(self):
        from candles_feed.hb_compat.data_types import CandlesConfig
        config = CandlesConfig(connector="binance", trading_pair="BTC-USDT")
        assert config.interval == "1m"
        assert config.max_records == 500

    def test_custom_values(self):
        from candles_feed.hb_compat.data_types import CandlesConfig
        config = CandlesConfig(
            connector="okx", trading_pair="ETH-USDT", interval="5m", max_records=1000
        )
        assert config.connector == "okx"
        assert config.interval == "5m"
        assert config.max_records == 1000

    def test_missing_required_raises(self):
        from candles_feed.hb_compat.data_types import CandlesConfig
        with pytest.raises(ValidationError):
            CandlesConfig(connector="binance")  # missing trading_pair


class TestHistoricalCandlesConfig:
    """HistoricalCandlesConfig must match hummingbot's fields exactly."""

    def test_all_fields(self):
        from candles_feed.hb_compat.data_types import HistoricalCandlesConfig
        config = HistoricalCandlesConfig(
            connector_name="binance",
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=1000000,
            end_time=2000000,
        )
        assert config.connector_name == "binance"
        assert config.trading_pair == "BTC-USDT"
        assert config.interval == "1m"
        assert config.start_time == 1000000
        assert config.end_time == 2000000

    def test_all_fields_required(self):
        from candles_feed.hb_compat.data_types import HistoricalCandlesConfig
        with pytest.raises(ValidationError):
            HistoricalCandlesConfig(connector_name="binance", trading_pair="BTC-USDT")


class TestUnsupportedConnectorError:
    """UnsupportedConnectorError must include connector name in message."""

    def test_message_includes_connector(self):
        from candles_feed.hb_compat.data_types import UnsupportedConnectorError
        exc = UnsupportedConnectorError("dydx")
        assert "dydx" in str(exc)

    def test_is_exception(self):
        from candles_feed.hb_compat.data_types import UnsupportedConnectorError
        assert issubclass(UnsupportedConnectorError, Exception)


class TestPublicAPI:
    """All public symbols must be importable from candles_feed.hb_compat."""

    def test_import_all_public_symbols(self):
        from candles_feed.hb_compat import (
            CandlesBaseAdapter,
            CandlesBaseProtocol,
            CandlesConfig,
            CandlesFactory,
            HistoricalCandlesConfig,
            UnsupportedConnectorError,
        )
        assert CandlesBaseAdapter is not None
        assert CandlesBaseProtocol is not None
        assert CandlesConfig is not None
        assert CandlesFactory is not None
        assert HistoricalCandlesConfig is not None
        assert UnsupportedConnectorError is not None
