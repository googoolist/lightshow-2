#!/bin/bash

# User-level installation script (no sudo required for Python packages)
# This script sets up the virtual environment and installs Python dependencies

echo "Audio-Reactive DMX Lighting System - User Installation"
echo "======================================================"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install it first with: sudo apt-get install python3 python3-venv python3-pip"
    exit 1
fi

# Remove old virtual environment if it exists
if [ -d "venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf venv
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

if [ ! -d "venv" ]; then
    echo "Error: Failed to create virtual environment"
    echo "You may need to install python3-venv:"
    echo "  sudo apt-get install python3-venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install numpy sounddevice aubio

# Link OLA Python bindings from system installation
echo "Linking OLA Python bindings..."
if [ -f "link_ola.sh" ]; then
    ./link_ola.sh
else
    echo "Warning: OLA linking script not found."
    echo "You may need to manually link OLA Python bindings."
fi

# Make scripts executable
chmod +x main.py 2>/dev/null || true
chmod +x run.sh 2>/dev/null || true

echo ""
echo "=========================================="
echo "Python environment setup complete!"
echo ""
echo "To test the installation:"
echo "  ./run.sh --check-deps"
echo ""
echo "To run the application:"
echo "  ./run.sh"
echo ""
echo "Note: You still need to install system dependencies if not already done:"
echo "  sudo bash setup_system.sh"
echo ""
echo "For automatic startup on boot (after system setup):"
echo "  sudo systemctl enable audio_dmx.service"