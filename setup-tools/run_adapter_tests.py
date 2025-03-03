"""
Helper script to run tests for a specific adapter.

This script ensures the package is in the Python path without needing to install it
and makes it easy to run tests for just one adapter.

Usage:
    python run_adapter_tests.py [adapter_name]
    
Examples:
    python run_adapter_tests.py binance_spot
    python run_adapter_tests.py okx_spot
    python run_adapter_tests.py kucoin_spot
"""

import os
import sys
import subprocess
from pathlib import Path

# Get the project root (parent directory of setup-tools)
project_root = Path(__file__).parent.parent.absolute()
package_dir = project_root / "candles_feed"

# Verify package directory exists
if not package_dir.exists():
    print(f"Error: Package directory not found at {package_dir}")
    sys.exit(1)

# Check for __init__.py
init_path = package_dir / "__init__.py"
if not init_path.exists():
    print(f"Error: __init__.py file not found at {init_path}")
    sys.exit(1)

print(f"Found package at: {package_dir}")
print(f"Project root is: {project_root}")

def get_available_adapters():
    """Get a list of available adapters from the package."""
    adapters_dir = project_root / "candles_feed" / "adapters"
    adapters = []
    
    if adapters_dir.exists() and adapters_dir.is_dir():
        for item in adapters_dir.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                adapters.append(item.name)
    
    return sorted(adapters)

def run_adapter_tests(adapter_name=None):
    """Run tests for a specific adapter or list available adapters."""
    available_adapters = get_available_adapters()
    
    # If no adapter specified, show the list of available adapters
    if not adapter_name:
        if len(sys.argv) > 1:
            adapter_name = sys.argv[1]
        else:
            print("\nAvailable adapters:")
            for adapter in available_adapters:
                print(f"  - {adapter}")
            print("\nUsage: python run_adapter_tests.py [adapter_name]")
            return 0
    
    # Check if the adapter exists
    if adapter_name not in available_adapters:
        print(f"Error: Adapter '{adapter_name}' not found.")
        print("Available adapters:")
        for adapter in available_adapters:
            print(f"  - {adapter}")
        return 1
    
    # Determine the test directory
    test_path = f"tests/unit/adapters/{adapter_name}"
    test_dir = project_root / test_path
    
    # Check if test directory exists
    if not test_dir.exists():
        # Try alternative paths
        alternative_paths = [
            f"tests/unit/adapters/{adapter_name.replace('_', '/')}",
            f"tests/unit/adapters/{adapter_name.split('_')[0]}/{adapter_name}"
        ]
        
        found = False
        for alt_path in alternative_paths:
            alt_dir = project_root / alt_path
            if alt_dir.exists():
                test_path = alt_path
                found = True
                break
        
        if not found:
            print(f"Warning: No tests found for adapter '{adapter_name}'.")
            print(f"Checked paths:")
            print(f"  - {test_path}")
            for alt_path in alternative_paths:
                print(f"  - {alt_path}")
            
            # Default to running with the first path anyway
            print(f"Attempting to run with path '{test_path}' anyway...")
    
    # Run the tests in a subprocess with modified environment
    # This approach bypasses any Python import system issues
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    
    print(f"Running tests for adapter: {adapter_name}")
    print(f"Test path: {test_path}")
    print(f"Setting PYTHONPATH to: {project_root}")
    
    # Try to use Hatch
    try:
        cmd = f"hatch run test {test_path}"
        print(f"Command: {cmd}")
        
        process = subprocess.run(
            cmd,
            shell=True,
            cwd=project_root,
            env=env,
            check=False  # Don't raise exception on non-zero exit
        )
        return process.returncode
    except FileNotFoundError:
        # If Hatch is not found, try pytest directly
        print("Hatch not found, trying pytest directly...")
        cmd = f"python -m pytest {test_path}"
        print(f"Command: {cmd}")
        
        process = subprocess.run(
            cmd,
            shell=True,
            cwd=project_root,
            env=env,
            check=False
        )
        return process.returncode

if __name__ == "__main__":
    # Run the tests
    adapter_name = sys.argv[1] if len(sys.argv) > 1 else None
    exit_code = run_adapter_tests(adapter_name)
    sys.exit(exit_code)