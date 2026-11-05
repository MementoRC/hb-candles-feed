"""Tests for the Lighter spot adapter (offline, fixture based)."""

from candles_feed.adapters.lighter.spot_adapter import LighterSpotAdapter
from tests.unit.adapters.lighter.lighter_contract import LighterAdapterContract


class TestLighterSpotAdapter(LighterAdapterContract):
    ADAPTER_CLS = LighterSpotAdapter
    SYMBOL = "ETH/USDC"
    MARKET_ID = 2048
    REGISTRY_NAME = "lighter_spot"
    CONNECTOR_NAME = "lighter"
