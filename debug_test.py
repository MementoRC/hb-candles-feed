#!/usr/bin/env python3
"""Debug test to identify the URL issue."""

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.adapters.binance.constants import SPOT_REST_URL, SPOT_CANDLES_ENDPOINT

def debug_binance_url():
    """Debug what URL the adapter is returning."""
    
    # Create adapter with explicit None network_config to ensure clean state
    adapter = BinanceSpotAdapter(network_config=None)
    # Ensure no residual network config from previous tests
    adapter.network_config = None
    
    # Get expected URL
    expected = f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
    
    # Get actual URL
    actual = adapter._get_rest_url()
    
    print(f"Expected URL: {expected}")
    print(f"Actual URL:   {actual}")
    print(f"URLs match: {actual == expected}")
    
    # Debug internal state
    print(f"\nAdapter attributes:")
    print(f"  network_config: {getattr(adapter, 'network_config', 'MISSING')}")
    print(f"  _bypass_network_selection: {getattr(adapter, '_bypass_network_selection', 'MISSING')}")
    
    # Check constants
    print(f"\nConstants:")
    print(f"  SPOT_REST_URL: {SPOT_REST_URL}")
    print(f"  SPOT_CANDLES_ENDPOINT: {SPOT_CANDLES_ENDPOINT}")
    
    # Test production URL method directly
    production_url = adapter._get_production_rest_url()
    print(f"  Production URL: {production_url}")
    
    return actual == expected

if __name__ == "__main__":
    success = debug_binance_url()
    print(f"\nDebug result: {'PASS' if success else 'FAIL'}")