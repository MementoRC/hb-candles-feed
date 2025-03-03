"""
PyCharm Setup Helper for Candles Feed Package

This script helps configure PyCharm to work with the candles_feed package
without installing it with pip. It verifies that Python can import the package
and provides debugging information.

Usage:
    1. Run this script from PyCharm or the command line
    2. If it fails, follow the setup instructions provided
"""
import os
import sys
from pathlib import Path

def test_import_in_subprocess():
    """Test importing the package in a subprocess with modified PYTHONPATH."""
    # Get the project root directory (parent of the setup-tools directory)
    project_dir = Path(__file__).parent.parent.absolute()
    package_dir = project_dir / "candles_feed"
    
    # Verify package directory exists
    if not package_dir.exists():
        print(f"Error: Package directory not found at {package_dir}")
        return False
        
    # Check for __init__.py
    init_path = package_dir / "__init__.py"
    if not init_path.exists():
        print(f"Error: __init__.py file not found at {init_path}")
        return False
    
    print(f"Package directory found at: {package_dir}")
    
    # Create a Python script to test importing the package
    test_script = """
import sys
print("Python path:")
for p in sys.path:
    print(f"  - {p}")
    
try:
    import candles_feed
    print(f"\\nSuccess! Imported candles_feed from {candles_feed.__file__}")
    
    # Try importing some submodules
    from candles_feed.core import candle_data
    print("Successfully imported candles_feed.core.candle_data")
    
    # Test importing base adapter
    from candles_feed.adapters import base_adapter
    print("Successfully imported candles_feed.adapters.base_adapter")
    
    sys.exit(0)
except ImportError as e:
    print(f"\\nError importing: {e}")
    sys.exit(1)
"""
    
    # Write the test script to a temporary file
    test_file = project_dir / "import_test.py"
    with open(test_file, "w") as f:
        f.write(test_script)
    
    try:
        # Create environment with modified PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_dir)
        
        # Run the test script
        print(f"\nRunning import test with PYTHONPATH={project_dir}")
        result = subprocess.run(
            [sys.executable, str(test_file)],
            env=env,
            text=True,
            capture_output=True
        )
        
        # Display output
        print("\nTest output:")
        print(result.stdout)
        
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        # Clean up
        test_file.unlink()
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running test: {e}")
        # Clean up
        if test_file.exists():
            test_file.unlink()
        return False

if __name__ == "__main__":
    # Get the project root directory (parent of the setup-tools directory)
    project_dir = Path(__file__).parent.parent.absolute()
    
    # Run the import test
    print("Testing package import using subprocess approach...")
    success = test_import_in_subprocess()
    
    if success:
        print("\nPyCharm configuration test PASSED!")
        print("The package is correctly importable when PYTHONPATH is set properly.")
    else:
        print("\nPyCharm configuration test FAILED!")
        print("The package cannot be imported. Check your PYTHONPATH configuration.")
    
    # Print PyCharm setup instructions
    print("\nPyCharm Setup Instructions:")
    print("1. Mark Source Directories:")
    print("   - Right-click on the 'candles-feed' directory in PyCharm")
    print("   - Select 'Mark Directory as' > 'Sources Root'")
    print("")
    print("2. Configure Run/Debug configurations:")
    print("   - Go to Run > Edit Configurations")
    print("   - For each configuration:")
    print("     * Set Working directory to the project root:")
    print(f"       {project_dir}")
    print("     * Add environment variable: PYTHONPATH={project_dir}")
    print("     * Check 'Add content roots to PYTHONPATH'")
    print("     * Check 'Add source roots to PYTHONPATH'")
    print("")
    print("3. Use the helper scripts:")
    print("   - run_tests_pycharm.py: Runs tests with proper PYTHONPATH")
    print("   - run_adapter_tests.py: Tests specific adapters")
    print("")
    print("4. Use Hatch (Recommended):")
    print(f"   $ cd {project_dir}")
    print("   $ hatch run test")
    print("   $ hatch run test-unit")
    print("")
    print("5. External Tools Configuration:")
    print("   - Go to Settings > Tools > External Tools")
    print("   - Add tools for common Hatch commands:")
    print("     * Name: Hatch Run Tests")
    print("     * Program: hatch")
    print("     * Arguments: run test")
    print(f"     * Working directory: {project_dir}")
    print("")
    print("Key Point: The most reliable approach is to set PYTHONPATH in your run configurations")
    print("           or use the helper scripts which do this automatically.")