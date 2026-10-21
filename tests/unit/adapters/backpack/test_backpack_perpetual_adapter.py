"""Tests for the Backpack perpetual adapter (offline, fixture based)."""

from candles_feed.adapters.backpack.perpetual_adapter import BackpackPerpetualAdapter
from tests.unit.adapters.backpack.backpack_contract import BackpackAdapterContract


class TestBackpackPerpetualAdapter(BackpackAdapterContract):
    ADAPTER_CLS = BackpackPerpetualAdapter
    SYMBOL = "BTC_USDC_PERP"
    REGISTRY_NAME = "backpack_perpetual"
    CONNECTOR_NAME = "backpack_perpetual"
