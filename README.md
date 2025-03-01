# A Hummingbot candles-feed sub-package

[![Template Package CI](https://github.com/hummingbot/hb-candles-feed/actions/workflows/ci.yml/badge.svg)](https://github.com/hummingbot/hb-candles-feed/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/hummingbot/hb-candles-feed)](https://codecov.io/gh/hummingbot/hb-candles-feed)
[![PyPI version](https://badge.fury.io/py/hummingbot-candles-feed.svg)](https://badge.fury.io/py/hummingbot-candles-feed)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A candles-feed package for Hummingbot that can later be moved to independent repositories.

## Overview

This package provides a functionality for developing Hummingbot sub-packages with:

- Modern Python packaging using scikit-build-core
- Cython integration for performance-critical code
- Complete CI/CD setup with GitHub Actions
- Comprehensive test suite structure
- Documentation templates and examples

## Features

- **Modular Architecture**: Clean separation of components with a registry pattern
- **Performance Optimization**: Decorator-based Cython compilation
- **Standalone Capability**: Works both within Hummingbot and as an independent package
- **Migration-Ready**: All configuration is designed for easy extraction to a separate repository
- **Developer Tools**: Development environment setup, test runners, and more

## Installation

### As a standalone package

```bash
# Clone the repository
git clone https://github.com/hummingbot/hb-candles-feed.git

# Navigate to the package directory
cd candles-feed

# Option 1: Install directly (requires Python 3.8+)
pip install .

# Option 2: Install with development dependencies
pip install -e ".[dev]"

# Option 3: Use conda setup (recommended)
./setup-dev-env.sh
```

### Building with Cython

This package uses Cython for performance-critical code. The Cython compilation is handled automatically during installation using scikit-build.

For manual compilation:

```bash
# Force recompilation of Cython modules
python cmake/cython_builder.py candles_feed
```

### As a dependency in your project

```bash
pip install hummingbot-candles-feed
```

## Usage

```python
import asyncio
from candles_feed import get_available_components
from candles_feed.core.registry import registry

async def main():
    # List available components
    components = get_available_components()
    print(f"Available components: {components}")
    
    # Create a component
    if "example_component" in components:
        component = registry.create_component(
            "example_component",
            "my_instance",
            {"setting": "value"}
        )
        
        # Initialize and start the component
        await component.initialize()
        await component.start()
        
        # Use the component
        # ...
        
        # Stop when done
        await component.stop()

# Run the example
asyncio.run(main())
```

## Project Structure

```
candles-feed/
├── CMakeLists.txt         # CMake configuration for Cython
├── MANIFEST.in            # Package file inclusions
├── README.md              # Package documentation
├── pyproject.toml         # Modern package configuration
├── run_tests.py           # Test runner script
├── setup-dev-env.sh       # Symlink to setup-tools/setup-dev-env.sh
├── setup.py               # Minimal setuptools wrapper
├── cmake/                 # CMake related files
│   ├── FindCython.cmake   # CMake helper for finding Cython
│   └── cython_builder.py  # Custom Cython compiler
├── setup-tools/           # Environment setup tools
│   ├── candles-feed-env.yml   # Conda environment specification
│   └── setup-dev-env.sh   # Development environment setup
├── candles_feed/      # Package code
│   └── __init__.py        # Package initialization
└── tests/                 # Test suite
    ├── README.md          # Test documentation
    ├── conftest.py        # Test fixtures and configuration
    ├── unit/              # Unit tests
    ├── integration/       # Integration tests
    └── e2e/               # End-to-end tests
```

## Running the Tests

```bash
# Option 1: Install dev dependencies using pip
pip install -e ".[dev]"

# Option 2: Use conda setup (recommended)
./setup-dev-env.sh

# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/e2e/

# Run with coverage
python -m pytest --cov=candles_feed

# Using the test runner script
./run_tests.py --all     # Run all tests
./run_tests.py --unit    # Run only unit tests
./run_tests.py --cov     # Run with coverage
```

## Customizing the Package

To customize this package:

1. Replace `candles_feed` with your package name throughout the codebase
2. Update metadata in `pyproject.toml`
3. Implement your components by extending `BaseComponent`
4. Register your components with the registry
5. Add tests for your components

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.