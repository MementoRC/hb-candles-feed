"""Live REST smoke tests for all exchange adapters.

Fetches a small number of candles from each exchange's public API
and validates basic data sanity. No authentication required.

Run with: pixi run test-unit tests/live/ -v -m live
Skip in CI: these tests hit real APIs and may be rate-limited.
"""

import time

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.network_client import NetworkClient

# Each entry: (registry_key, trading_pair, interval, expected_min_candles)
# Trading pairs chosen for high liquidity on each exchange.
CONNECTOR_TEST_CASES = [
    # Spot adapters
    ("ascend_ex_spot", "BTC-USDT", "1m", 3),
    ("binance_spot", "BTC-USDT", "1m", 3),
    ("bitget_spot", "BTC-USDT", "1m", 3),
    ("btc_markets_spot", "BTC-AUD", "1m", 3),
    ("bybit_spot", "BTC-USDT", "1m", 3),
    ("coinbase_advanced_trade", "BTC-USD", "1m", 3),
    ("dexalot_spot", "AVAX-USDC", "5m", 0),  # Dexalot DEX: low liquidity, may return 0
    ("gate_io_spot", "BTC-USDT", "1m", 3),
    ("hyperliquid_spot", "BTC-USDC", "1m", 3),
    ("kraken_spot", "BTC-USD", "1m", 3),
    ("kucoin_spot", "BTC-USDT", "1m", 3),
    ("mexc_spot", "BTC-USDT", "1m", 3),
    ("okx_spot", "BTC-USDT", "1m", 3),
    # Perpetual adapters
    ("aevo_perpetual", "BTC-USDC", "1m", 3),
    ("binance_perpetual", "BTC-USDT", "1m", 3),
    ("bitget_perpetual", "BTC-USDT", "1m", 3),
    ("bitmart_perpetual", "BTC-USDT", "1m", 3),
    ("bybit_perpetual", "BTC-USDT", "1m", 3),
    ("gate_io_perpetual", "BTC-USDT", "1m", 3),
    ("hyperliquid_perpetual", "BTC-USDC", "1m", 3),
    ("kucoin_perpetual", "BTC-USDT", "1m", 3),
    ("mexc_perpetual", "BTC-USDT", "1m", 3),
    ("okx_perpetual", "BTC-USDT", "1m", 3),
    ("pacifica_perpetual", "BTC-USDC", "1m", 3),
]


def _connector_id(val):
    """Generate readable test IDs from parametrize tuples."""
    if isinstance(val, tuple):
        return val[0]
    return str(val)


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "registry_key,trading_pair,interval,min_candles",
    CONNECTOR_TEST_CASES,
    ids=[c[0] for c in CONNECTOR_TEST_CASES],
)
async def test_rest_fetch_candles(
    registry_key: str,
    trading_pair: str,
    interval: str,
    min_candles: int,
):
    """Smoke test: fetch candles from live exchange REST API.

    Validates:
    - Adapter can be instantiated from registry
    - REST endpoint returns data
    - Response parses into valid CandleData objects
    - Timestamps are recent (within last 7 days)
    - OHLCV values are positive
    - High >= Low for each candle
    """
    adapter = ExchangeRegistry.get_adapter(registry_key)
    assert adapter is not None, f"Adapter {registry_key} not found in registry"

    async with NetworkClient() as client:
        candles = await adapter.fetch_rest_candles(
            trading_pair=trading_pair,
            interval=interval,
            limit=10,
            network_client=client,
        )

    # Basic response validation
    assert isinstance(candles, list), f"{registry_key}: expected list, got {type(candles)}"
    assert len(candles) >= min_candles, (
        f"{registry_key}: expected >= {min_candles} candles, got {len(candles)}"
    )

    now = time.time()
    seven_days_ago = now - (7 * 24 * 3600)

    for i, candle in enumerate(candles):
        prefix = f"{registry_key}[{i}]"

        # Type check
        assert isinstance(candle, CandleData), f"{prefix}: not CandleData"

        # Timestamp sanity: should be within last 7 days
        assert candle.timestamp > seven_days_ago, (
            f"{prefix}: timestamp {candle.timestamp} is older than 7 days"
        )
        assert candle.timestamp <= now + 120, (
            f"{prefix}: timestamp {candle.timestamp} is in the future"
        )

        # Price sanity
        assert candle.open > 0, f"{prefix}: open={candle.open} not positive"
        assert candle.high > 0, f"{prefix}: high={candle.high} not positive"
        assert candle.low > 0, f"{prefix}: low={candle.low} not positive"
        assert candle.close > 0, f"{prefix}: close={candle.close} not positive"

        # OHLC consistency
        assert candle.high >= candle.low, (
            f"{prefix}: high={candle.high} < low={candle.low}"
        )
        assert candle.high >= candle.open, (
            f"{prefix}: high={candle.high} < open={candle.open}"
        )
        assert candle.high >= candle.close, (
            f"{prefix}: high={candle.high} < close={candle.close}"
        )
        assert candle.low <= candle.open, (
            f"{prefix}: low={candle.low} > open={candle.open}"
        )
        assert candle.low <= candle.close, (
            f"{prefix}: low={candle.low} > close={candle.close}"
        )

        # Volume: non-negative (Aevo returns 0 for mark-price-only data)
        assert candle.volume >= 0, f"{prefix}: volume={candle.volume} negative"


@pytest.mark.live
@pytest.mark.asyncio
async def test_all_connectors_registered():
    """Verify all expected connectors are in the ExchangeRegistry."""
    registered = ExchangeRegistry.get_registered_exchanges()
    expected = {c[0] for c in CONNECTOR_TEST_CASES}

    missing = expected - set(registered)
    assert not missing, f"Missing from registry: {missing}"


@pytest.mark.live
@pytest.mark.asyncio
async def test_factory_roundtrip():
    """Verify CandlesFactory can create adapters for all hummingbot connector names."""
    from candles_feed.hb_compat.data_types import CandlesConfig
    from candles_feed.hb_compat.factory import CandlesFactory

    for connector_name in CandlesFactory.get_supported_connectors():
        config = CandlesConfig(connector=connector_name, trading_pair="BTC-USDT")
        adapter = CandlesFactory.get_candle(config)
        assert adapter is not None, f"Factory returned None for {connector_name}"
