#!/bin/bash
# setup-dev-env.sh

set -e

# Function to activate the environment
activate_env() {
    echo "Activating environment: $1"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source "$1/Scripts/activate"
    else
        source "$1/bin/activate"
    fi
}

# Check if conda is available
if command -v conda &> /dev/null; then
    echo "Setting up development environment with conda..."
    
    # Create or update the hummingbot environment
    if conda env list | grep -q "hummingbot"; then
        echo "Using existing hummingbot environment"
        eval "$(conda shell.bash hook)"
        conda activate hummingbot
    else
        echo "Creating new hummingbot environment"
        conda create -n hummingbot python=3.9 -y
        eval "$(conda shell.bash hook)"
        conda activate hummingbot
    fi
    
    # Install development dependencies
    pip install scikit-build-core cython cmake wheel pytest pytest-asyncio
    
    # Install candles-feed in development mode
    cd "$(dirname "$0")"
    pip install -e ".[dev]"
    
    echo "Development environment is ready! Activated conda environment: hummingbot"
else
    echo "Conda not found, setting up with regular Python..."
    
    # Create a virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python -m venv venv
    fi
    
    # Activate virtual environment
    activate_env "venv"
    
    # Install development dependencies
    pip install scikit-build-core cython cmake wheel pytest pytest-asyncio
    
    # Install candles-feed in development mode
    cd "$(dirname "$0")"
    pip install -e ".[dev]"
    
    echo "Development environment is ready! Activated virtual environment: venv"
fi

# Run a simple verification
echo ""
echo "Verifying installation..."
python -c "import candles_feed; print(f'candles-feed package found, version: {candles_feed.__version__}')"
echo "Success!"