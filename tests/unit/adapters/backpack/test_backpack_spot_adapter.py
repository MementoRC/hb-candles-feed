"""Tests for the Backpack spot adapter (offline, fixture based)."""

from candles_feed.adapters.backpack.spot_adapter import BackpackSpotAdapter
from tests.unit.adapters.backpack.backpack_contract import BackpackAdapterContract


class TestBackpackSpotAdapter(BackpackAdapterContract):
    ADAPTER_CLS = BackpackSpotAdapter
    SYMBOL = "BTC_USDC"
    REGISTRY_NAME = "backpack_spot"
    CONNECTOR_NAME = "backpack"
