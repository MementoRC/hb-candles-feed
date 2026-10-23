"""Upstream hummingbot names consumed from hb_compat (parity G10 + G11, issue #86)."""

import pytest

UPSTREAM_INTERVAL_TO_SECONDS = {
    "1s": 1,
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
    "1M": 2592000,
}

UPSTREAM_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_asset_volume",
    "n_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]

UPSTREAM_MESSAGE = (
    "Timestamp is not in a recognized format. "
    "Must be in seconds, milliseconds, microseconds or nanoseconds."
)


def test_top_level_imports():
    from candles_feed.hb_compat import (  # noqa: F401
        CandlesBaseAdapter,
        CandlesConfig,
        CandlesFactory,
        HistoricalCandlesConfig,
        UnsupportedConnectorError,
        UnsupportedConnectorException,
    )


def test_factory_module_exports_exception():
    from candles_feed.hb_compat.factory import UnsupportedConnectorException  # noqa: F401


@pytest.mark.parametrize(("interval", "seconds"), UPSTREAM_INTERVAL_TO_SECONDS.items())
def test_interval_to_seconds_class_level(interval, seconds):
    from candles_feed.hb_compat import CandlesBaseAdapter

    assert CandlesBaseAdapter.interval_to_seconds[interval] == seconds


def test_interval_to_seconds_exact_mapping():
    from candles_feed.hb_compat import CandlesBaseAdapter

    assert dict(CandlesBaseAdapter.interval_to_seconds) == UPSTREAM_INTERVAL_TO_SECONDS


def test_columns_class_level():
    from candles_feed.hb_compat import CandlesBaseAdapter

    assert CandlesBaseAdapter.columns == UPSTREAM_COLUMNS


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1_700_000_000, 1_700_000_000),
        (1_700_000_000_000, 1_700_000_000),
        (1_700_000_000_000_000, 1_700_000_000),
        (1_700_000_000_000_000_000, 1_700_000_000),
        (1_700_000_000.9, 1_700_000_000),
        ("1700000000000", 1_700_000_000),
    ],
)
def test_adapter_ensure_timestamp_in_seconds(value, expected):
    from candles_feed.hb_compat import CandlesBaseAdapter

    assert CandlesBaseAdapter.ensure_timestamp_in_seconds(value) == expected


def test_adapter_ensure_timestamp_too_small():
    from candles_feed.hb_compat import CandlesBaseAdapter

    with pytest.raises(ValueError, match="recognized format") as exc:
        CandlesBaseAdapter.ensure_timestamp_in_seconds(123)
    assert str(exc.value) == UPSTREAM_MESSAGE


def test_exception_alias_identity():
    from candles_feed.hb_compat import UnsupportedConnectorError, UnsupportedConnectorException

    assert UnsupportedConnectorException is UnsupportedConnectorError


def test_exception_message_matches_upstream():
    from candles_feed.hb_compat import UnsupportedConnectorException

    exc = UnsupportedConnectorException("dydx")
    assert str(exc) == "The connector dydx is not available. Please select another one."
    assert exc.connector == "dydx"


def test_factory_raises_upstream_named_exception():
    from candles_feed.hb_compat import CandlesConfig, CandlesFactory
    from candles_feed.hb_compat.factory import UnsupportedConnectorException

    config = CandlesConfig(connector="dydx", trading_pair="BTC-USDT")
    with pytest.raises(UnsupportedConnectorException, match="dydx"):
        CandlesFactory.get_candle(config)
