#!/usr/bin/env python3
"""
Test runner script for the Candles Feed package.

Usage:
    python run_tests.py [options]

Options:
    --unit           Run unit tests
    --integration    Run integration tests
    --e2e            Run end-to-end tests
    --all            Run all tests
    --cov            Generate coverage report
    --html           Generate HTML report
    --adapter=NAME   Run tests for specific adapter
"""

import argparse
import subprocess
import sys


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run tests for Candles Feed package")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--cov", action="store_true", help="Generate coverage report")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--adapter", help="Run tests for specific adapter")
    return parser.parse_args()


def run_tests(args):
    """Run tests based on arguments."""
    cmd = ["pytest", "-v"]

    # Add coverage if requested
    if args.cov:
        cmd.extend(["--cov=candles_feed", "--cov-report=term"])
        if args.html:
            cmd.append("--cov-report=html")

    # Add HTML report if requested
    if args.html and not args.cov:
        cmd.append("--html=report.html")

    # Determine which tests to run
    if args.all:
        # Run all tests
        pass
    elif args.unit:
        cmd.append("tests/unit/")
    elif args.integration:
        cmd.append("tests/integration/")
    elif args.e2e:
        cmd.append("tests/e2e/")
    elif args.adapter:
        cmd.append(f"tests/unit/adapters/{args.adapter}/")
    else:
        # Default: run unit tests
        cmd.append("tests/unit/")

    # Run the tests
    process = subprocess.run(cmd)
    return process.returncode


def main():
    """Main entry point."""
    args = parse_args()
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())
