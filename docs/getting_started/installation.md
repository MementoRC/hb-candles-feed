# Installation

This guide will walk you through the process of installing the Candles Feed framework and setting up your environment.

## Prerequisites

Before installing the framework, ensure you have:

1. Python 3.8 or later
2. pip (Python package installer)
3. Virtual environment tool (optional but recommended)

## Installation Options

### Option 1: Install from PyPI (Recommended)

The easiest way to install the Candles Feed framework is from PyPI:

```bash
pip install hummingbot-candles-feed
```

### Option 2: Install from Source

To install the latest development version, you can clone the repository and install it directly:

```bash
# Clone the repository
git clone https://github.com/hummingbot/hummingbot.git

# Navigate to the project directory
cd hummingbot/sub-packages/candles-feed

# Install the package in development mode
pip install -e .
```

### Option 3: Using a Virtual Environment (Recommended)

It's recommended to install the framework in a virtual environment to avoid conflicts with other packages:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the package
pip install hummingbot-candles-feed
```

## Dependencies

The framework has the following core dependencies:

- `numpy`: For numerical operations
- `pandas`: For data manipulation and analysis
- `aiohttp`: For asynchronous HTTP requests
- `websockets`: For WebSocket communication
- `pydantic`: For data validation and settings management

These dependencies will be automatically installed when you install the framework.

## Verify Installation

To verify that the installation was successful, run the following in a Python interpreter:

```python
>>> from candles_feed import CandlesFeed
>>> from candles_feed.core.exchange_registry import ExchangeRegistry
>>> ExchangeRegistry.discover_adapters()
>>> print(ExchangeRegistry.list_available_adapters())
```

This should output a list of available exchange adapters.

## Optional Dependencies

For development, testing, and documentation, you may want to install additional packages:

```bash
# Development dependencies
pip install -e ".[dev]"

# Documentation dependencies
pip install -e ".[doc]"
```

## Troubleshooting

If you encounter issues during installation, try the following:

### Common Issues

1. **Package not found**:
   ```
   ERROR: Could not find a version that satisfies the requirement hummingbot-candles-feed
   ```
   
   Solution: The package might not be available on PyPI yet. Try installing from source.

2. **Dependency conflicts**:
   ```
   ERROR: Cannot install hummingbot-candles-feed due to package conflicts
   ```
   
   Solution: Use a virtual environment to avoid conflicts with existing packages.

3. **Permission errors**:
   ```
   ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
   ```
   
   Solution: Use `pip install --user` or consider using a virtual environment.

### Getting Help

If you continue to experience issues, you can:

1. Check the [GitHub Issues](https://github.com/hummingbot/hummingbot/issues) page
2. Open a new issue with details about your setup and the error you're encountering
3. Join the community discussion on Discord or other channels

## Next Steps

Now that you have installed the Candles Feed framework, you can:

1. Follow the [Quick Start](quick_start.md) guide to begin using the framework
2. Explore the API Reference for detailed documentation
3. Learn about the architecture and core components