# Template Setup Tools

This directory contains tools to help set up and manage the template package.

## Tools

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

### `candles-feed-env.yml`

Conda environment specification for the template package. Used by `setup-dev-env.sh` to create a consistent development environment.

### `setup-dev-env.sh`

Shell script to set up a development environment using conda. It creates or updates a conda environment with all the dependencies required for development.

```bash
# Run from the template package root directory
./setup-dev-env.sh
```

## Using These Tools

The typical workflow for creating a new sub-package is:

1. Run `create_subpackage.py` to create a new package based on the template
2. Change to the newly created package directory
3. Run `setup-dev-env.sh` to set up the development environment
4. Run tests to verify the package works
5. Start implementing your package functionality

For example:

```bash
# Create a new package
./create_subpackage.py --name market-data

# Change to the new package directory
cd ../market-data

# Set up the development environment
./setup-dev-env.sh

# Run the unit tests
python -m pytest tests/unit/
```