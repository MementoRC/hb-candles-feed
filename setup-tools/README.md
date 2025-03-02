# Candles Feed Development Tools

This directory contains tools to help set up and manage the Candles Feed package.

## Tools

### `candles-feed-env.yml`

Conda environment specification for the Candles Feed package. This file defines all dependencies needed for development, testing, and building.

### `setup-dev-env.sh`

Shell script to set up a development environment using conda. It creates or updates a conda environment with all the dependencies required for development.

```bash
# Run from the package root directory
./setup-tools/setup-dev-env.sh
```

## Setting Up the Development Environment

### Using Conda (Recommended)

1. Create a new conda environment:
   ```bash
   conda env create -f setup-tools/candles-feed-env.yml
   ```

2. Activate the environment:
   ```bash
   conda activate hb-candles-feed
   ```

3. Use Hatch commands for development:
   ```bash
   # Run the OKX perpetual adapter tests
   hatch run test-perpetual
   
   # Run all unit tests
   hatch run test-unit
   
   # Format code
   hatch run format
   
   # Lint code
   hatch run lint
   
   # Run all checks (format, lint, typecheck, test)
   hatch run check
   ```

### Benefits of Using Hatch

- **Consistent Environments**: Hatch ensures all developers use the same environment settings
- **Simple Commands**: Common tasks have simple, standardized commands
- **Integrated Testing**: Run tests without installing the package
- **Conda Integration**: Works with conda for better scientific package management
- **No Installation Required**: Test and develop without installing the package

## Creating New Adapters

When creating new exchange adapters, follow these steps:

1. Create a new directory structure:
   ```
   candles_feed/adapters/exchange_name_market_type/
   ```

2. Create the necessary files:
   - `__init__.py`
   - `constants.py`
   - `exchange_name_market_type_adapter.py`

3. Create test files:
   ```
   tests/unit/adapters/exchange_name_market_type/
   ```

4. Run your tests:
   ```bash
   hatch run test-unit
   ```

## Testing Without Installation

Hatch lets you run tests without installing the package. This is especially useful for testing new adapters like the OKX perpetual adapter:

```bash
hatch run test-perpetual
```