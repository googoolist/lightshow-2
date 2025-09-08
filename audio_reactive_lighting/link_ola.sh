#!/bin/bash

# Script to link system OLA Python bindings to virtual environment

echo "Linking OLA Python bindings to virtual environment..."

# Find Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Common locations for OLA Python bindings
OLA_PATHS=(
    "/usr/lib/python$PYTHON_VERSION/dist-packages/ola"
    "/usr/lib/python3/dist-packages/ola"
    "/usr/local/lib/python$PYTHON_VERSION/dist-packages/ola"
    "/usr/local/lib/python3/dist-packages/ola"
)

# Find OLA installation
OLA_FOUND=""
for path in "${OLA_PATHS[@]}"; do
    if [ -d "$path" ]; then
        OLA_FOUND="$path"
        echo "Found OLA at: $path"
        break
    fi
done

if [ -z "$OLA_FOUND" ]; then
    echo "Error: OLA Python bindings not found in system."
    echo "Please install OLA first:"
    echo "  sudo apt-get install ola ola-python"
    exit 1
fi

# Link to virtual environment
VENV_SITE_PACKAGES="venv/lib/python$PYTHON_VERSION/site-packages"

if [ ! -d "$VENV_SITE_PACKAGES" ]; then
    echo "Error: Virtual environment not found or has different structure"
    echo "Please run ./install_user.sh first"
    exit 1
fi

# Create symbolic link
ln -sfn "$OLA_FOUND" "$VENV_SITE_PACKAGES/ola"

echo "Successfully linked OLA to virtual environment!"
echo ""
echo "You can now run:"
echo "  ./run.sh"