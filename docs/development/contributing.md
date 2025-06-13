# Contributing Guidelines

This document provides detailed guidelines for contributing to the Candles Feed Framework. For a comprehensive overview, see the main CONTRIBUTING.md file in the project root.

## Quick Start for Contributors

### 1. Set Up Development Environment

```bash
# Clone the repository
git clone https://github.com/MementoRC/hb-candles-feed.git
cd hb-candles-feed

# Using Pixi (recommended)
pixi install
pixi shell

# Or using Hatch
hatch env create dev
hatch shell dev

# Verify setup
pixi run test  # or hatch run dev:test
```

### 2. Development Workflow

1. Create a feature branch from `development`
2. Make your changes following [coding standards](coding_standards.md)
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

### 3. Quality Checks

Before submitting your changes:

```bash
# Run tests
pixi run test

# Check code formatting
pixi run lint
pixi run format

# Run type checking
pixi run typecheck

# Run pre-commit hooks
pixi run pre-commit run --all-files
```

## Code Review Guidelines

### For Contributors

- **Small PRs**: Keep pull requests focused and reasonably sized
- **Clear Description**: Explain what your changes do and why
- **Link Issues**: Reference related issues or feature requests
- **Documentation**: Update docs for user-facing changes
- **Tests**: Include comprehensive tests for new functionality

### For Reviewers

- **Be Constructive**: Provide helpful feedback and suggestions
- **Check Tests**: Verify that tests cover the new functionality
- **Verify Documentation**: Ensure changes are properly documented
- **Consider Impact**: Think about backward compatibility and performance
- **Security**: Review for potential security implications

## Testing Requirements

### Test Categories

1. **Unit Tests**: Test individual components
   ```bash
   pixi run test-unit
   ```

2. **Integration Tests**: Test component interactions
   ```bash
   pixi run test-integration
   ```

3. **End-to-End Tests**: Test complete workflows
   ```bash
   pixi run test tests/e2e/
   ```

4. **Performance Tests**: Benchmark critical operations
   ```bash
   pixi run test -m benchmark
   ```

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestNewFeature:
    """Test suite for new feature."""
    
    async def test_basic_functionality(self):
        """Test that basic functionality works."""
        # Arrange
        expected_result = "test_value"
        
        # Act
        result = await your_function()
        
        # Assert
        assert result == expected_result
    
    async def test_error_handling(self):
        """Test error conditions are handled properly."""
        with pytest.raises(ValueError, match="Invalid input"):
            await your_function(invalid_input)
    
    @pytest.mark.benchmark
    async def test_performance(self, benchmark):
        """Test performance characteristics."""
        result = benchmark(your_function)
        assert result is not None
```

## Documentation Standards

### API Documentation

- Use Sphinx-style docstrings
- Include parameter types and descriptions
- Document exceptions that may be raised
- Provide usage examples

```python
async def fetch_candles(
    trading_pair: str,
    interval: str,
    limit: int = 100
) -> list[dict]:
    """Fetch candles from the exchange.
    
    :param trading_pair: Trading pair symbol (e.g., 'BTC-USDT')
    :param interval: Time interval for candles ('1m', '5m', '1h', etc.)
    :param limit: Maximum number of candles to fetch (default: 100)
    :return: List of candle data dictionaries
    :raises ValueError: If trading pair format is invalid
    :raises ConnectionError: If unable to connect to exchange
    
    Example:
        >>> candles = await fetch_candles('BTC-USDT', '1m', 50)
        >>> print(f"Received {len(candles)} candles")
    """
```

### User Documentation

- Write clear, step-by-step instructions
- Include working code examples
- Explain configuration options
- Cover common troubleshooting scenarios

## Release Process

### Version Management

- **Semantic Versioning**: MAJOR.MINOR.PATCH
- **Automated Releases**: Triggered by conventional commit messages
- **Release Notes**: Auto-generated from commit history

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Examples:
```
feat(adapters): add support for new exchange
fix(core): resolve memory leak in data processor
docs(examples): add WebSocket usage example
test(integration): improve mock server reliability
```

### Release Types

- `feat`: New features (minor version bump)
- `fix`: Bug fixes (patch version bump)
- `feat!` or `BREAKING CHANGE`: Breaking changes (major version bump)
- `docs`, `test`, `refactor`, `style`, `chore`: No version bump

## Community Guidelines

### Communication

- **Be Respectful**: Treat all community members with respect
- **Be Patient**: Remember that contributors have different experience levels
- **Be Constructive**: Provide helpful feedback and suggestions
- **Be Inclusive**: Welcome contributors from all backgrounds

### Getting Help

1. **Documentation**: Check the [documentation site](https://mementorc.github.io/hb-candles-feed/)
2. **GitHub Issues**: Search existing issues or create a new one
3. **GitHub Discussions**: Ask questions and share ideas
4. **Code Review**: Request help during the PR review process

### Reporting Issues

When reporting bugs:

1. Use the issue template
2. Provide minimal reproduction steps
3. Include environment details
4. Add relevant logs or error messages
5. Describe expected vs. actual behavior

### Suggesting Features

When requesting features:

1. Use the feature request template
2. Explain the use case and motivation
3. Describe the proposed solution
4. Consider alternatives and their trade-offs
5. Assess impact on existing functionality

## Maintainer Guidelines

### Release Management

1. **Quality Gates**: Ensure all tests pass and quality checks succeed
2. **Documentation**: Verify documentation is updated
3. **Breaking Changes**: Clearly communicate any breaking changes
4. **Migration Guides**: Provide migration instructions when needed

### Issue Triage

- **Label Issues**: Apply appropriate labels for categorization
- **Prioritize**: Set priority based on impact and effort
- **Assign**: Assign to appropriate maintainers or contributors
- **Close**: Close resolved, duplicate, or invalid issues

### PR Review Process

1. **Automated Checks**: Verify CI/CD pipeline passes
2. **Code Review**: Review for quality, style, and correctness
3. **Testing**: Ensure adequate test coverage
4. **Documentation**: Verify documentation updates
5. **Approval**: Approve when ready to merge

---

For more detailed information, see the main CONTRIBUTING.md file in the project root.