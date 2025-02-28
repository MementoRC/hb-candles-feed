# Standalone Testing Guide for hb-candles-feed

This guide provides steps for testing the candles-feed package as a standalone repository while maintaining its ability to work within Hummingbot.

## Setting Up the Standalone Repository

### 1. Create a GitHub Repository

1. Log in to your GitHub account
2. Create a new repository named "hb-candles-feed"
3. Do not initialize it with README, .gitignore, or license

### 2. Initialize Git in the Local Directory

```bash
# Navigate to the candles-feed directory
cd /home/memento/ClaudeCode/candles-feed/hummingbot/sub-packages/candles-feed

# Initialize git
git init

# Add all files
git add .

# Make initial commit
git commit -m "Initial commit of candles-feed package"
```

### 3. Connect to Your GitHub Repository

```bash
# Add your GitHub repository as remote
git remote add origin https://github.com/MementoRC/hb-candles-feed.git

# Push to GitHub
git push -u origin main
```

### 4. Enable GitHub Actions

1. Go to your repository on GitHub
2. Navigate to the Actions tab
3. Click "I understand my workflows, go ahead and enable them"

## Testing the Package Locally

### 1. Set Up Development Environment

```bash
# Navigate to the candles-feed directory
cd /home/memento/ClaudeCode/candles-feed/hummingbot/sub-packages/candles-feed

# Run the development setup script
./setup-dev-env.sh
```

### 2. Run Tests

```bash
# Run all tests
./run_tests.py --all

# OR run specific test categories
./run_tests.py --unit
./run_tests.py --integration
```

### 3. Build the Package

```bash
# Build the package
python -m build
```

## Integration with GitHub Services (Optional)

### CodeCov Integration

1. Sign up for an account at codecov.io using your GitHub account
2. Add your repository to CodeCov
3. Add your CodeCov token as a GitHub repository secret:
   - Name: `CODECOV_TOKEN`
   - Value: Your token from CodeCov

### PyPI Deployment

1. Register an account on PyPI
2. Create an API token
3. Add your PyPI token as a GitHub repository secret:
   - Name: `PYPI_API_TOKEN`
   - Value: Your token from PyPI

## Dual-Mode Usage Notes

This package is configured to function in two modes:

1. **Within Hummingbot**: As a sub-package within the Hummingbot repository
2. **Standalone**: As an independent package in its own repository

### Path-Aware Code

The CI/CD workflows are designed to detect which mode they're running in:

```yaml
# Detect if we're in a standalone repo or within Hummingbot
if [ -d "../../hummingbot" ]; then
  # We're in the Hummingbot monorepo
  pip install -e ".[dev]"
else
  # We're in a standalone repo
  pip install -e ".[dev]"
fi
```

### Importing in Either Mode

For other code that needs to use this package:

```python
# Try importing as standalone package first
try:
    from candles_feed.core import CandlesFeed
# Fall back to Hummingbot sub-package path
except ImportError:
    from hummingbot.sub_packages.candles_feed.candles_feed.core import CandlesFeed
```

## Returning to Hummingbot

Remember that the primary usage will be within Hummingbot. The standalone repository is mainly for testing and development. Any significant changes should be synchronized back to the Hummingbot repository.