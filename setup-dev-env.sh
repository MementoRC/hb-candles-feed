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
        
        # Update the environment with the latest dependencies
        echo "Updating environment with latest dependencies..."
        conda env update -f "$ENV_FILE" --prune
    else
        echo "Creating new hb-candles-feed environment from environment file"
        conda env create -f "$ENV_FILE"
        activate_conda_env "hb-candles-feed"
    fi
    
    # Get package name from directory name
    PACKAGE_NAME=$(basename "$PACKAGE_ROOT" | tr '-' '_')
    PACKAGE_DIR="$PACKAGE_ROOT/$PACKAGE_NAME"
    
    # Check if the package has an adequate structure
    STRUCTURE_READY=false
    if [ -d "$PACKAGE_DIR" ] && [ -f "$PACKAGE_DIR/__init__.py" ]; then
        # Check if it has actual content (more than just a basic init file)
        if [ $(find "$PACKAGE_DIR" -type f | wc -l) -gt 1 ]; then
            STRUCTURE_READY=true
        fi
    fi
    
    # Display message about Hatch
    echo ""
    echo "==================================================================="
    echo "Development environment is ready with Hatch integration."
    echo "You can run the following commands from the package root:"
    echo ""
    echo "  hatch run test            # Run all tests"
    echo "  hatch run test-unit       # Run unit tests"
    echo "  hatch run test-perpetual  # Run OKX perpetual adapter tests"
    echo "  hatch run format          # Format code with ruff"
    echo "  hatch run lint            # Lint code with ruff"
    echo "  hatch run check           # Run all checks and tests"
    echo ""
    echo "For more commands, see the 'scripts' section in pyproject.toml"
    echo "==================================================================="
    echo ""
   
    # Only install the package if explicitly requested
    if [ "$1" == "--install" ]; then
        if $STRUCTURE_READY; then
            # Install package in development mode if requested
            echo "Package structure detected. Installing in development mode..."
            cd "$PACKAGE_ROOT"
            pip install -e .
            
            # Verify installation
            echo ""
            echo "Verifying installation..."
            python -c "import $PACKAGE_NAME; print(f'$PACKAGE_NAME package found')"
            echo "Success!"
        else
            echo "Package structure not complete. Skipping installation."
        fi
    else
        echo "Package not installed. Using Hatch for development."
        echo "If you need to install the package, run: $0 --install"
    fi
    
    # Show active environment
    echo ""
    echo "Active conda environment: $(conda info --envs | grep '*' | awk '{print $1}')"
else
    echo "Error: Conda is required for development."
    echo "Please install conda from https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi