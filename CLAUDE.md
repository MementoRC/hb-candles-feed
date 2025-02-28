# Hummingbot Sub-Package Development Guide

This document summarizes the approach and best practices for developing modular, standalone sub-packages within the Hummingbot ecosystem that can later be migrated to independent repositories.

## Architecture Overview

We've created a modular architecture for Hummingbot sub-packages with these key principles:

1. **Independent Functionality**: Each sub-package should be self-contained with minimal dependencies on the main Hummingbot code
2. **Standalone Capability**: Sub-packages should work both within Hummingbot and as independent packages
3. **Migration-Ready**: All package configuration is designed for easy extraction to a separate repository
4. **Modern Build System**: Using scikit-build-core and CMake for Cython integration

## Build System Implementation

### Core Components

1. **pyproject.toml**: Modern Python packaging standard
   ```toml
   [build-system]
   requires = [
       "scikit-build-core>=0.5.0",
       "Cython>=0.29.33",
       "setuptools>=42.0.0",
       "wheel>=0.37.0",
       "cmake>=3.21.0"
   ]
   build-backend = "scikit_build_core.build"
   
   [project]
   name = "hummingbot-candles-feed"
   # ... other package metadata
   
   [tool.scikit-build]
   wheel.packages = ["candles_feed"]
   cmake.source-dir = "."
   build.parallel = true
   ```

2. **CMakeLists.txt**: Cython build configuration
   ```cmake
   cmake_minimum_required(VERSION 3.21)
   project(candles_feed)

   # Set Python as the required language
   find_package(Python REQUIRED COMPONENTS Interpreter Development)
   find_package(Cython REQUIRED)

   # Include directory configuration
   include_directories(${Python_INCLUDE_DIRS})

   # Add our custom Cython build module
   add_custom_target(build_cython ALL
       COMMAND ${Python_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/cython_builder.py ${CMAKE_CURRENT_SOURCE_DIR}/candles_feed
       WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
       COMMENT "Running Cython builder"
   )
   ```

3. **cython_builder.py**: Custom Cython compilation
   ```python
   # This script auto-detects files with @cython decorator and compiles them
   # Usage: python cython_builder.py [src_dir]
   ```

4. **setup.py**: Backward compatibility wrapper
   ```python
   # Minimal setup.py for pip install compatibility
   from setuptools import setup
   setup()
   ```

## Code Organization

1. **Directory Structure**:
   ```
   hummingbot/
   └── sub-packages/
       └── candles-feed/
           ├── .github/             # GitHub Actions & configs (dormant in Hummingbot)
           ├── candles_feed/        # Main package code
           ├── docs/                # Documentation
           ├── tests/               # Test suite
           ├── CMakeLists.txt       # CMake config for Cython
           ├── MANIFEST.in          # Package file inclusion
           ├── pyproject.toml       # Modern package config
           ├── README.md            # Package documentation
           ├── setup.py             # Minimal setup.py
           └── cython_builder.py    # Custom Cython compiler
   ```

2. **Import Structure**: Ensure imports work both in Hummingbot and standalone
   ```python
   # Prefer relative imports within the package
   from .core import candle_data
   
   # For absolute imports, use the package name directly
   from candles_feed.core import candle_data
   
   # AVOID Hummingbot-specific import paths
   # from hummingbot.sub-packages.candles-feed import ...
   ```

## CI/CD Implementation

### Standalone CI/CD Pipeline

1. **CI Workflow** (.github/workflows/ci.yml):
   - Matrix testing on multiple Python versions
   - Runs tests, coverage, and linting
   - Builds and verifies the package
   - Path-aware to work in both Hummingbot and standalone contexts

2. **Publishing Workflow** (.github/workflows/publish.yml):
   - Triggered by GitHub releases or manual dispatch
   - Builds and validates the package
   - Publishes to PyPI

3. **GitHub Configuration Files**:
   - CODEOWNERS
   - Issue and PR templates
   - Release configuration
   - Dependabot setup
   - CodeCov configuration

## Development Environment

1. **setup-dev-env.sh**: Script to create development environment
   ```bash
   # Setting up development environment
   # Detects venv/conda and installs in appropriate mode
   python -m pip install -e ".[dev]"
   ```

2. **Testing Configuration**:
   ```toml
   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   asyncio_default_fixture_loop_scope = "function"
   testpaths = ["tests"]
   markers = [
       "unit: marks tests as unit tests",
       "integration: marks tests as integration tests",
       "e2e: marks tests as end-to-end tests",
   ]
   ```

## Integration with Hummingbot

1. **Independence from Hummingbot Core**:
   - Minimize dependencies on Hummingbot internals
   - Use interfaces and adapters to connect with Hummingbot
   - Keep exchange-specific code isolated in adapter modules

2. **Installation within Hummingbot**:
   ```python
   # In Hummingbot's setup.py
   extras_require={
       "candles": [
           "candles_feed @ file:./sub-packages/candles-feed"
       ],
   }
   ```

## Documentation Standards

1. **README.md**: Complete usage instructions that work for both contexts
2. **API Documentation**: Focus on public interfaces
3. **Examples**: Standalone examples that work outside Hummingbot

## Testing Strategy

1. **Test Categories**:
   - Unit tests: Core functionality testing
   - Integration tests: Exchange adapter testing
   - End-to-end tests: Complete workflow testing

2. **Mock Exchange Servers**: For testing without real API calls
3. **Fixtures**: Reusable test components for various exchange responses

## Cython Optimization Strategy

1. **Decorator-Based Approach**: Use `@cython` decorator to mark functions for optimization
2. **Auto-Detection**: `cython_builder.py` detects and compiles decorated functions
3. **Performance-Critical Areas**: Focus on data processing and high-frequency operations

## Migration Strategy

When migrating to a standalone repository:
1. Copy the sub-package directory to a new repository
2. Update any Hummingbot-specific imports
3. CI/CD will work immediately due to the standalone configuration
4. Update documentation references to the new repository

## Common Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=candles_feed

# Build the package
python -m build

# Force recompilation of Cython modules
python cython_builder.py candles_feed
```

## Best Practices

1. **Versioning**: Use semantic versioning
2. **Documentation**: Keep documentation up-to-date with code changes
3. **Testing**: Maintain high test coverage, especially for exchange adapters
4. **Dependencies**: Minimize external dependencies
5. **Error Handling**: Robust error handling for exchange communication
6. **Logging**: Structured logging with appropriate levels
7. **Configuration**: Use environment variables and config files for settings
8. **API Design**: Create clean, well-documented interfaces