# Template Setup Tools

This directory contains tools to help set up and manage the template package with Hatch integration.

## Tools

### `hatch-hooks/`

This directory contains custom build hooks for Hatch that replace the need for separate CMake configuration:

- **`cython_build_hook.py`**: Automatically detects and compiles Python modules with `@cython` decorators during the build process, eliminating the need for CMake scripts.

### `create_subpackage.py`

A script to create a new Hummingbot sub-package based on this template. It copies the template directory and replaces all template-specific names and identifiers with your new package name.

```bash
# Create a new package with default settings (creates sibling directory)
./create_subpackage.py --name your-package-name

# Create a package with custom description and output directory
./create_subpackage.py --name your-package-name --description "Your package description" --output-dir ~/projects/

# Create a package at exact location (don't append package name to path)
./create_subpackage.py --name your-package-name --output-dir ~/projects/exact-location --exact-path
```

#### Improvements in the latest version

The script now handles:

1. **More thorough replacements**: Converts all template-specific references to your new package name
2. **Proper URL updates**: Updates GitHub and documentation URLs
3. **Cleanup of duplicate files**: Removes any duplicate package directories that might be created
4. **Removal of nested setup.py files**: Cleans up unnecessary nested setup files
5. **Syntax fixes**: Automatically fixes common issues like missing commas in pyproject.toml
6. **Proper README updates**: Updates badge URLs and project descriptions
7. **Hatch integration**: Sets up Hatch for project management and development workflows
8. **Simplified CMake integration**: Uses Hatch hooks instead of separate CMake files

### `hatch-hooks/`

Directory containing Hatch build hooks that replace CMake for Cython compilation:

- **`cython_build_hook.py`** - Automatically detects and compiles Python modules marked with `@cython` decorator

### `setup-dev-env.sh`

Shell script to set up a development environment using conda based on the dependencies defined in pyproject.toml.

```bash
# Run from the template package root directory to set up the environment
./setup-dev-env.sh

# If you need to install the package in development mode
./setup-dev-env.sh --install
```

This script reads dependency information directly from pyproject.toml and installs them into a conda environment, eliminating the need for a separate environment.yml file. It handles both conda and pip dependencies, including pip packages that need the `--no-deps` flag.

The environment configuration in pyproject.toml supports both regular and pip dependencies with the `--no-deps` flag:

```toml
# Regular dependencies (installed via conda)
[tool.hatch.envs.default.dependencies]
dependencies = [
  "pandas>=1.0.0",
  "numpy>=1.20.0",
]

# Dependencies installed with pip --no-deps
[tool.hatch.envs.default.pip-no-deps]
dependencies = [
  "hatch-conda>=0.5.2",
  "some-package==1.0.0",
]
```

## Using These Tools with Hatch

The typical workflow for creating a new sub-package is:

1. Run `create_subpackage.py` to create a new package based on the template
2. Change to the newly created package directory
3. Run `setup-dev-env.sh` to set up the development environment
4. Use Hatch commands to run tests, format code, and more
5. Start implementing your package functionality

### Simplified Package Structure

This template uses a streamlined approach with modern Python packaging:

- **pyproject.toml**: Primary configuration file defining all package metadata, dependencies, build settings, and tool configurations
- **Hatch**: Used for environment management, testing, linting, and building
- **Optional files**: setup.py is included for compatibility but isn't required

When creating a new package, you can safely remove:
- setup.py (if you don't need to support legacy tools)

For example:

```bash
# Create a new package
./create_subpackage.py --name market-data

# Change to the new package directory
cd ../market-data

# Set up the development environment with Hatch
./setup-dev-env.sh

# Run all tests using Hatch
hatch run test

# Run just the unit tests
hatch run test-unit

# Format code
hatch run format

# Lint code
hatch run lint

# Run all checks (format, lint, typecheck, test)
hatch run check
```

## Benefits of Hatch Integration

- **Simplified Development**: Run tests and development tools without installing the package
- **Consistent Environments**: All developers use the same settings and commands
- **Conda Integration**: Works with conda environments for scientific computing dependencies
- **Predefined Scripts**: Common tasks have standardized, easy-to-remember commands
- **Multiple Environments**: Define separate environments for docs, testing, etc.
