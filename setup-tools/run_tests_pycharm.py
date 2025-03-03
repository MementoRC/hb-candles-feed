"""
Helper script to run tests directly from PyCharm.

This script ensures the package is in the Python path without needing to install it.
It uses Hatch under the hood to handle dependencies and pytest configuration.

Usage:
    Run this script directly in PyCharm with the Python interpreter

You can pass command line arguments to pytest:
    python run_tests_pycharm.py tests/unit/
    python run_tests_pycharm.py -v tests/unit/adapters/
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# Get the project root (parent directory of setup-tools)
project_root = Path(__file__).parent.parent.absolute()

# The simplest approach: Use a subprocess with modified environment

def run_tests_in_subprocess():
    """Run tests in a subprocess with modified PYTHONPATH."""
    # Get command line arguments to pass to the test command
    args = sys.argv[1:] or ["tests/"]
    arg_string = " ".join(args)
    
    # Create environment with the right path
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    
    # Try to use Hatch
    try:
        hatch_cmd = f"hatch run test {arg_string}"
        print(f"Running: {hatch_cmd}")
        result = subprocess.run(
            hatch_cmd,
            shell=True,
            cwd=project_root,
            env=env,
            check=False
        )
        return result.returncode
    except FileNotFoundError:
        # If Hatch is not found, try pytest directly
        try:
            pytest_cmd = f"python -m pytest {arg_string}"
            print(f"Hatch not found. Running: {pytest_cmd}")
            result = subprocess.run(
                pytest_cmd,
                shell=True,
                cwd=project_root,
                env=env,
                check=False
            )
            return result.returncode
        except Exception as e:
            print(f"Error running tests: {e}")
            return 1

# Remove old function as we've replaced it with run_tests_in_subprocess

if __name__ == "__main__":
    # Run the tests using the subprocess approach
    print(f"Running tests from: {project_root}")
    print(f"Setting PYTHONPATH to: {project_root}")
    exit_code = run_tests_in_subprocess()
    sys.exit(exit_code)