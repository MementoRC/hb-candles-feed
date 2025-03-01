#!/bin/bash
# setup-dev-env.sh

set -e

# Get the script's location, handling both direct execution and symlinks
SCRIPT_PATH="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT_PATH" ]; do
    SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"
    SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
    [[ $SCRIPT_PATH != /* ]] && SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_PATH"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"

# Determine if we're in the setup-tools directory or the project root
if [[ "$(basename "$SCRIPT_DIR")" == "setup-tools" ]]; then
    PACKAGE_ROOT="$(dirname "$SCRIPT_DIR")"
    ENV_FILE="$SCRIPT_DIR/candles-feed-env.yml"
else
    # We're in the project root via symlink
    PACKAGE_ROOT="$SCRIPT_DIR"
    ENV_FILE="$PACKAGE_ROOT/setup-tools/candles-feed-env.yml"
fi

echo "Package root detected as: $PACKAGE_ROOT"
echo "Using environment file: $ENV_FILE"

# Verify environment file exists
if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: Environment file not found at $ENV_FILE"
    exit 1
fi

# Function to activate the conda environment
activate_conda_env() {
    eval "$(conda shell.bash hook)"
    conda activate "$1"
}

# Check if conda is available
if command -v conda &> /dev/null; then
    echo "Setting up development environment with conda..."
    
    # Check if hummingbot environment exists
    if conda env list | grep -q "^hummingbot "; then
        echo "Found existing hummingbot environment. Adding required packages..."
        activate_conda_env "hummingbot"
        
        # Install required packages from our environment file
        conda env update -f "$ENV_FILE" --prune
    # Check if hb-candles-feed environment exists
    elif conda env list | grep -q "^hb-candles-feed "; then
        echo "Using existing hb-candles-feed environment"
        activate_conda_env "hb-candles-feed"
    else
        echo "Creating new hb-candles-feed environment from environment file"
        conda env create -f "$ENV_FILE"
        activate_conda_env "hb-candles-feed"
    fi
    
    # Get package name from directory name
    PACKAGE_NAME=$(basename "$PACKAGE_ROOT" | tr '-' '_')
    PACKAGE_DIR="$PACKAGE_ROOT/$PACKAGE_NAME"
    
    # Check if the package has an adequate structure for installation
    STRUCTURE_READY=false
    if [ -d "$PACKAGE_DIR" ] && [ -f "$PACKAGE_DIR/__init__.py" ]; then
        # Check if it has actual content (more than just a basic init file)
        if [ $(find "$PACKAGE_DIR" -type f | wc -l) -gt 1 ]; then
            STRUCTURE_READY=true
        fi
    fi
    
    if $STRUCTURE_READY; then
        # Install package in development mode
        echo "Package structure detected. Installing in development mode..."
        cd "$PACKAGE_ROOT"
        pip install -e .
        echo "Development environment is ready! Activated conda environment: $(conda info --envs | grep '*' | awk '{print $1}')"
    else
        echo ""
        echo "======================================================================================="
        echo "NOTICE: Package structure at '$PACKAGE_DIR' is not complete yet."
        echo ""
        echo "This is normal for a newly created package scaffold. The development environment"
        echo "will be set up with all dependencies, but the package itself won't be installed."
        echo ""
        echo "Next steps:"
        echo "1. Create or complete the package structure in: $PACKAGE_DIR"
        echo "   Make sure to create at least: $PACKAGE_DIR/__init__.py"
        echo ""
        echo "2. Add your implementation files"
        echo ""
        echo "3. Run this script again to install the package in development mode"
        echo "======================================================================================="
        echo ""
        
        # Install development dependencies directly
        cd "$PACKAGE_ROOT"
        
        # Install common dev dependencies directly
        echo "Installing development dependencies..."
        pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-timeout ruff mypy build
        
        echo "Development environment is ready! Activated conda environment: $(conda info --envs | grep '*' | awk '{print $1}')"
    fi
else
    echo "Error: Conda is required for development."
    echo "Please install conda from https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Run a simple verification only if package is installed
if $STRUCTURE_READY; then
    echo ""
    echo "Verifying installation..."
    python -c "import $PACKAGE_NAME; print(f'$PACKAGE_NAME package found')"
    echo "Success!"
else
    echo ""
    echo "Run this script again after creating the package structure to install and verify the package."
fi