"""Tests for the Lighter perpetual adapter (offline, fixture based)."""

from candles_feed.adapters.lighter.perpetual_adapter import LighterPerpetualAdapter
from tests.unit.adapters.lighter.lighter_contract import LighterAdapterContract


class TestLighterPerpetualAdapter(LighterAdapterContract):
    ADAPTER_CLS = LighterPerpetualAdapter
    SYMBOL = "ETH"
    MARKET_ID = 0
    REGISTRY_NAME = "lighter_perpetual"
    CONNECTOR_NAME = "lighter_perpetual"
