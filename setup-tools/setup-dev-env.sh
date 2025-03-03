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
else
    # We're in the project root via symlink
    PACKAGE_ROOT="$SCRIPT_DIR"
fi

echo "Package root detected as: $PACKAGE_ROOT"
echo "Using pyproject.toml for environment configuration"

# Verify pyproject.toml exists
if [[ ! -f "$PACKAGE_ROOT/pyproject.toml" ]]; then
    echo "Error: pyproject.toml not found at $PACKAGE_ROOT/pyproject.toml"
    exit 1
fi

# Function to activate the conda environment
activate_conda_env() {
    eval "$(conda shell.bash hook)"
    conda activate "$1"
}

# Check if conda is available
if command -v conda &> /dev/null; then
    echo "Setting up development environment with Hatch..."
    
    # Make sure conda is available first
    echo "Ensuring conda is available..."
    
    # No need to activate base - we'll directly create our environment with hatch
    
    # Change to the package root directory to ensure hatch finds pyproject.toml
    cd "$PACKAGE_ROOT"
    
    echo "Setting up environment from pyproject.toml..."
    
    # Extract the project name from pyproject.toml to use as conda env name
    PROJECT_NAME=$(grep -m 1 "name" $PACKAGE_ROOT/pyproject.toml | sed 's/.*"\(.*\)".*/\1/' | sed 's/hb-//')
    CONDA_ENV="hb-$PROJECT_NAME"
    
    echo "Project name: $PROJECT_NAME"
    echo "Conda environment name: $CONDA_ENV"
    
    # Check if conda environment already exists
    if conda env list | grep -q "^$CONDA_ENV "; then
        echo "Using existing conda environment: $CONDA_ENV"
        activate_conda_env "$CONDA_ENV"
        
        # Update environment if needed
        echo "Updating environment dependencies..."
        # Manually install dependencies by using conda and pip
        echo "Installing dependencies from pyproject.toml..."
        
        # Core dependencies (use conda)
        # Extract dependencies from pyproject.toml
        DEPENDENCIES=$(grep -A 20 "\[tool.hatch.envs.default.dependencies\]" "$PACKAGE_ROOT/pyproject.toml" | grep -E '^\s+"[^"]+"' | sed 's/^[[:space:]]*"\(.*\)",*/\1/g')
        
        # Install them into the conda environment
        if [ ! -z "$DEPENDENCIES" ]; then
            echo "Installing conda dependencies..."
            # Install each dependency (ignore errors, as some might need pip)
            for dep in $DEPENDENCIES; do
                conda install -n "$CONDA_ENV" -c conda-forge $dep -y || true
            done
        fi
        
        # Install pip dependencies using --no-deps
        PIP_DEPS=$(grep -A 10 "\[tool.hatch.envs.default.pip-no-deps\]" "$PACKAGE_ROOT/pyproject.toml" | grep -E '^\s+"[^"]+"' | sed 's/^[[:space:]]*"\(.*\)",*/\1/g')
        
        if [ ! -z "$PIP_DEPS" ]; then
            echo "Installing pip dependencies with --no-deps..."
            for dep in $PIP_DEPS; do
                echo "Installing $dep"
                pip install --no-deps $dep || true
            done
        fi
    else
        # Create a new conda environment directly
        echo "Creating new conda environment: $CONDA_ENV"
        
        # First create a minimal conda environment
        conda create -n "$CONDA_ENV" python=3.10 hatch -y
        
        # Activate it
        activate_conda_env "$CONDA_ENV"
        
        # Manually install dependencies by using conda and pip (same as the update case)
        echo "Installing dependencies from pyproject.toml..."
        
        # Core dependencies (use conda)
        # Extract dependencies from pyproject.toml
        DEPENDENCIES=$(grep -A 20 "\[tool.hatch.envs.default.dependencies\]" "$PACKAGE_ROOT/pyproject.toml" | grep -E '^\s+"[^"]+"' | sed 's/^[[:space:]]*"\(.*\)",*/\1/g')
        
        # Install them into the conda environment
        if [ ! -z "$DEPENDENCIES" ]; then
            echo "Installing conda dependencies..."
            # Install each dependency (ignore errors, as some might need pip)
            for dep in $DEPENDENCIES; do
                conda install -n "$CONDA_ENV" -c conda-forge $dep -y || true
            done
        fi
        
        # Install pip dependencies using --no-deps
        PIP_DEPS=$(grep -A 10 "\[tool.hatch.envs.default.pip-no-deps\]" "$PACKAGE_ROOT/pyproject.toml" | grep -E '^\s+"[^"]+"' | sed 's/^[[:space:]]*"\(.*\)",*/\1/g')
        
        if [ ! -z "$PIP_DEPS" ]; then
            echo "Installing pip dependencies with --no-deps..."
            for dep in $PIP_DEPS; do
                echo "Installing $dep"
                pip install --no-deps $dep || true
            done
        fi
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
    echo "  hatch run test-integration # Run integration tests"
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