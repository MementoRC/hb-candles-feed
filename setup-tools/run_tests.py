#!/usr/bin/env python
"""
Test runner script for the candles-feed package

This script provides a convenient way to run different types of tests
with various options.

Usage:
    ./run_tests.py [OPTIONS]

Options:
    --all         Run all tests
    --unit        Run unit tests
    --integration Run integration tests
    --e2e         Run end-to-end tests
    --cov         Run with coverage
    --verbose     Run with verbose output
    --component=X Run tests for specific component (e.g. --component=core)
"""

import argparse
import subprocess
import sys


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run template package tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    parser.add_argument("--component", type=str, help="Run tests for specific component")
    parser.add_argument("--cov", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", action="store_true", help="Run with verbose output")
    
    args = parser.parse_args()
    
    # If no test type specified, default to --unit
    if not any([args.all, args.unit, args.integration, args.e2e]):
        args.unit = True
        
    return args


def build_command(args):
    """Build the pytest command based on arguments."""
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage if requested
    if args.cov:
        cmd.append("--cov=candles_feed")
        cmd.append("--cov-report=term")
        cmd.append("--cov-report=xml")
    
    # Add test selection
    test_paths = []
    test_marks = []
    
    if args.all:
        test_paths.append("tests/")
    else:
        if args.unit:
            test_marks.append("unit")
            test_paths.append("tests/unit/")
        if args.integration:
            test_marks.append("integration")
            test_paths.append("tests/integration/")
        if args.e2e:
            test_marks.append("e2e")
            test_paths.append("tests/e2e/")
    
    # Add component filter if specified
    if args.component:
        for i, path in enumerate(test_paths):
            if not path.endswith("/"):
                path += "/"
            test_paths[i] = path + args.component + "/"
    
    # Add the paths to the command
    cmd.extend(test_paths)
    
    # Add markers if we're not using paths directly
    if test_marks and not test_paths:
        marker_expr = " or ".join(test_marks)
        cmd.append(f"-m '{marker_expr}'")
    
    return cmd


def main():
    """Main entry point for the test runner."""
    args = parse_args()
    cmd = build_command(args)
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with exit code {e.returncode}")
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())