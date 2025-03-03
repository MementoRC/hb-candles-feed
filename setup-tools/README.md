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

### `test_path_setup.py`

A diagnostic tool to verify that your Python environment can correctly import the candles-feed package without installation. It provides detailed instructions for configuring IDEs like PyCharm.

```bash
# Run from the setup-tools directory
python test_path_setup.py
```

### `run_tests_pycharm.py`

A helper script for running tests from PyCharm without installing the package. It sets up the Python path correctly and uses Hatch to run the tests.

```bash
# Run from the setup-tools directory in PyCharm
python run_tests_pycharm.py [test_path]
```

### `run_adapter_tests.py`

A specialized script for testing individual exchange adapters. It helps navigate the test directory structure and run tests for a specific adapter.

```bash
# Run from the setup-tools directory
python run_adapter_tests.py [adapter_name]
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

### Using PyCharm Without Installing the Package

You can use PyCharm to develop and test the package without using `pip install -e`. This approach allows for a cleaner development environment and better compatibility with Hatch.

#### Method 1: Using the Bootstrap Runner (Recommended)

This is the most reliable method for running tests from within PyCharm:

1. Create a new Run/Debug Configuration in PyCharm:
   - Go to Run → Edit Configurations
   - Click the + to add a new Python configuration
   - Set Script path to: `pycharm_config.py`
   - Set Parameters to: `tests/unit/your_test_file.py` (or other test path)
   - Set Working directory to: `/home/memento/ClaudeCode/candles-feed/hummingbot/sub-packages/candles-feed`
   - Click Apply and OK

2. Run this configuration to execute your test with the proper path setup.

#### Method 2: Using Debug Scripts

These diagnostic scripts help troubleshoot import issues:

1. **Run the diagnostic tool**:
   ```bash
   cd setup-tools
   python debug_pycharm.py
   ```
   This will show detailed information about Python path and import issues.

2. **Use specialized test runners**:
   - `setup-tools/run_pytest.py` - Runs pytest directly with correct paths
   - `setup-tools/bootstrap_test.py` - Advanced test runner with module finder

3. **Configure PyCharm basics**:
   - Mark the `candles-feed` directory as "Sources Root"
   - Add the project directory to the Python interpreter paths
   - Configure run configurations with the correct working directory

#### Method 3: External Hatch Tool Integration

Set up External Tools for easy Hatch access:

1. Go to Settings > Tools > External Tools
2. Create a new tool:
   - Name: Hatch Run Tests
   - Program: hatch
   - Arguments: run test
   - Working directory: $ProjectFileDir$
3. Add similar tools for other commands (format, lint, etc.)

#### Running Tests in PyCharm

We've provided several scripts to handle different testing scenarios:

1. **`run_unit_tests.py`**: Runs only unit tests, skipping integration and e2e tests that require external services
   ```bash
   # From PyCharm, create a configuration that runs:
   python setup-tools/run_unit_tests.py
   ```

2. **`run_pytest.py`**: Runs pytest with arguments, good for targeted test runs
   ```bash
   # From PyCharm, create a configuration that runs:
   python setup-tools/run_pytest.py tests/unit/core
   ```

3. **`direct_run.py`**: Uses Hatch directly, bypassing Python's import system
   ```bash
   # From PyCharm, create a configuration that runs:
   python setup-tools/direct_run.py
   ```

#### How the Scripts Bypass Installation

These helper scripts use a simple but effective technique to make the package importable without installation:

1. They run tests in a subprocess with a modified environment
2. The `PYTHONPATH` environment variable is set to include the project root
3. This ensures Python looks in the correct directory first
4. No modification to sys.path or sys.modules is needed in your main environment

This subprocess-based approach is the most reliable way to handle Python imports without installing packages, especially with complex Python packages.

These configurations enable a smooth development workflow in PyCharm while leveraging Hatch for dependency management and task automation.