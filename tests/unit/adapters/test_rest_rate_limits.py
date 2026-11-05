"""Pin the documented per-exchange REST rate limits (#93 phase 2).

The table below is the single source of truth for the declared values; each row is
backed by a source citation next to the declaration in the adapter module and in
``docs/adapters/rest_rate_limits.md``.
"""

import pytest

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.rate_limiter import (
    DEFAULT_REST_RATE_LIMIT,
    RestRateLimit,
    get_adapter_rate_limiter,
    pool_key_for,
    reset_rate_limiters,
)

ExchangeRegistry.discover_adapters()

# name -> (max_requests, period_seconds, explicit pool or None for the per-class pool)
DECLARED: dict[str, tuple[int, float, str | None]] = {
    "aevo_perpetual": (120, 60, None),
    "backpack_perpetual": (6000, 60, "backpack"),
    "backpack_spot": (6000, 60, "backpack"),
    "binance_perpetual": (600, 60, None),
    "binance_spot": (1200, 60, None),
    "bitget_perpetual": (20, 1, None),
    "bitget_spot": (20, 1, None),
    "bitmart_perpetual": (12, 2, None),
    "btc_markets_spot": (50, 10, None),
    "bybit_perpetual": (49, 1, "bybit"),
    "bybit_spot": (49, 1, "bybit"),
    "coinbase_advanced_trade": (10, 1, None),
    "decibel_perpetual": (400, 60, None),
    "dexalot_spot": (200, 60, None),
    "evedex_perpetual": (1200, 60, None),
    "gate_io_perpetual": (300, 1, None),
    "gate_io_spot": (200, 2, None),
    "grvt_perpetual": (1200, 60, None),
    "hyperliquid_perpetual": (1200, 60, "hyperliquid"),
    "hyperliquid_spot": (1200, 60, "hyperliquid"),
    "kraken_spot": (1, 1, None),
    "kucoin_perpetual": (666, 30, None),
    "kucoin_spot": (1333, 30, None),
    "lighter_perpetual": (60, 60, "lighter"),
    "lighter_spot": (60, 60, "lighter"),
    "mexc_perpetual": (20, 2, None),
    "mexc_spot": (20000, 60, None),
    "okx_perpetual": (20, 2, "okx"),
    "okx_spot": (20, 2, "okx"),
    "pacifica_perpetual": (10, 60, None),
}

# name -> (host connector pool limit_id, weight per klines request); used only when a host
# connector throttler is shared (#89). Adapters absent here keep (None, 1).
HOST_POOL: dict[str, tuple[str, int]] = {
    "binance_perpetual": ("REQUEST_WEIGHT", 1),
    "binance_spot": ("REQUEST_WEIGHT", 1),
    "bybit_perpetual": ("GETLimit", 1),
    "bybit_spot": ("ALL", 1),
    "decibel_perpetual": ("DECIBEL_LIMIT", 1),
    "coinbase_advanced_trade": ("PUBLIC_REST_REQUESTS", 1),
    "dexalot_spot": ("IP_REQUEST_WEIGHT", 1),
    "evedex_perpetual": ("REQUEST_WEIGHT", 1),
    "gate_io_perpetual": ("PublicPoints", 1),
    "gate_io_spot": ("PublicPoints", 1),
    "grvt_perpetual": ("grvtGlobalRateLimit", 1),
    "hyperliquid_perpetual": ("All", 1),
    "hyperliquid_spot": ("All", 1),
    "kraken_spot": ("PublicEndpointLimitID", 1),
    "lighter_perpetual": ("lighter_perpetual_all", 300),
    "lighter_spot": ("lighter_all", 300),
    "mexc_spot": ("IP_REQUEST_WEIGHT", 1),
    "pacifica_perpetual": ("PACIFICA_LIMIT", 12),
}

# No locally verifiable REST limit: these keep the framework default.
UNDOCUMENTED = {"ascend_ex_spot"}

SHARED_POOLS = [
    ("backpack_spot", "backpack_perpetual"),
    ("bybit_spot", "bybit_perpetual"),
    ("hyperliquid_spot", "hyperliquid_perpetual"),
    ("lighter_spot", "lighter_perpetual"),
    ("okx_spot", "okx_perpetual"),
]

SEPARATE_POOLS = [
    ("binance_spot", "binance_perpetual"),
    ("bitget_spot", "bitget_perpetual"),
    ("gate_io_spot", "gate_io_perpetual"),
    ("kucoin_spot", "kucoin_perpetual"),
    ("mexc_spot", "mexc_perpetual"),
]


def _adapter(name: str) -> type[BaseAdapter]:
    return ExchangeRegistry.get_adapter_class(name)  # type: ignore[return-value]


def _shipped_names() -> set[str]:
    return {
        name
        for name, cls in ExchangeRegistry._adapters.items()
        if cls.__module__.startswith("candles_feed.adapters.")
    }


@pytest.fixture(autouse=True)
def _clean_limiters():
    reset_rate_limiters()
    yield
    reset_rate_limiters()


@pytest.mark.parametrize("name", sorted(DECLARED))
def test_declared_limit_and_pool(name: str) -> None:
    max_requests, period, pool = DECLARED[name]
    adapter = _adapter(name)
    declared_limit, declared_pool = adapter.REST_RATE_LIMIT, adapter.REST_RATE_LIMIT_POOL
    assert declared_limit == RestRateLimit(max_requests, period)
    assert declared_pool == pool


@pytest.mark.parametrize("name", sorted(set(DECLARED) | UNDOCUMENTED))
def test_declared_host_pool_and_weight(name: str) -> None:
    adapter = _adapter(name)
    expected = HOST_POOL.get(name, (None, 1))
    assert expected == (adapter.REST_HOST_RATE_LIMIT_ID, adapter.REST_HOST_RATE_LIMIT_WEIGHT)


@pytest.mark.parametrize("name", sorted(UNDOCUMENTED))
def test_undocumented_adapters_use_default(name: str) -> None:
    adapter = _adapter(name)
    assert adapter.REST_RATE_LIMIT == DEFAULT_REST_RATE_LIMIT
    assert adapter.REST_RATE_LIMIT_POOL is None


def test_every_shipped_adapter_is_declared_or_explicitly_undocumented() -> None:
    shipped = _shipped_names()
    assert shipped == set(DECLARED) | UNDOCUMENTED
    assert not set(DECLARED) & UNDOCUMENTED


@pytest.mark.parametrize(("first", "second"), SHARED_POOLS)
def test_variants_sharing_an_exchange_budget_share_one_limiter(first: str, second: str) -> None:
    assert pool_key_for(_adapter(first)) == pool_key_for(_adapter(second))
    assert get_adapter_rate_limiter(_adapter(first)) is get_adapter_rate_limiter(_adapter(second))


@pytest.mark.parametrize("names", SHARED_POOLS)
def test_shared_pool_variants_declare_identical_limits(names: tuple[str, str]) -> None:
    first, second = (_adapter(n) for n in names)
    assert first.REST_RATE_LIMIT == second.REST_RATE_LIMIT


def _pool_members() -> dict[str, list[type[BaseAdapter]]]:
    pools: dict[str, list[type[BaseAdapter]]] = {}
    for name in sorted(_shipped_names()):
        cls = _adapter(name)
        pools.setdefault(pool_key_for(cls), []).append(cls)
    return {key: members for key, members in pools.items() if len(members) > 1}


@pytest.mark.parametrize("pool", sorted(_pool_members()))
def test_every_shared_pool_declares_identical_limit(pool: str) -> None:
    """Members of one pool share one budget, so REST_RATE_LIMIT must match exactly.

    The host link (REST_HOST_RATE_LIMIT_ID / weight) may differ per variant: it is a
    per-adapter, per-connector pairing and the bridge names its limit by pool + host id.
    """
    members = _pool_members()[pool]
    assert len({m.REST_RATE_LIMIT for m in members}) == 1


@pytest.mark.parametrize(("first", "second"), SEPARATE_POOLS)
def test_variants_with_separate_budgets_get_separate_limiters(first: str, second: str) -> None:
    assert pool_key_for(_adapter(first)) != pool_key_for(_adapter(second))
    assert get_adapter_rate_limiter(_adapter(first)) is not get_adapter_rate_limiter(
        _adapter(second)
    )


def test_host_pool_names_only_declared_adapters() -> None:
    assert set(HOST_POOL) <= set(DECLARED)


def test_resolved_limiter_carries_the_declared_limit() -> None:
    assert get_adapter_rate_limiter(_adapter("kraken_spot")).limit == RestRateLimit(1, 1)
