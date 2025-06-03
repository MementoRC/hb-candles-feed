#!/usr/bin/env python3
"""Debug test sequence issues."""

import pytest
from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.adapters.binance.constants import SPOT_REST_URL, SPOT_CANDLES_ENDPOINT
from tests.unit.adapters.binance.test_binance_spot_adapter import TestBinanceSpotAdapter

def test_direct_creation():
    """Test creating adapter directly."""
    test_instance = TestBinanceSpotAdapter()
    adapter = test_instance.create_adapter()
    
    expected = test_instance.get_expected_rest_url()
    actual = adapter._get_rest_url()
    
    print(f"Direct creation:")
    print(f"  Expected: {expected}")
    print(f"  Actual:   {actual}")
    print(f"  Match:    {actual == expected}")
    print(f"  network_config: {getattr(adapter, 'network_config', 'MISSING')}")
    
    return actual == expected

def test_fixture_creation():
    """Test creating adapter via fixture method."""
    test_instance = TestBinanceSpotAdapter()
    adapter = test_instance.adapter()  # This is what the fixture calls
    
    expected = test_instance.get_expected_rest_url()
    actual = adapter._get_rest_url()
    
    print(f"Fixture creation:")
    print(f"  Expected: {expected}")
    print(f"  Actual:   {actual}")
    print(f"  Match:    {actual == expected}")
    print(f"  network_config: {getattr(adapter, 'network_config', 'MISSING')}")
    
    return actual == expected

if __name__ == "__main__":
    print("=== Testing Adapter Creation Methods ===")
    
    result1 = test_direct_creation()
    print()
    result2 = test_fixture_creation()
    
    print(f"\nResults:")
    print(f"  Direct creation: {'PASS' if result1 else 'FAIL'}")
    print(f"  Fixture creation: {'PASS' if result2 else 'FAIL'}")