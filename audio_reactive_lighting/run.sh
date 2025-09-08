#!/bin/bash

# Run script for Audio-Reactive DMX Lighting System
# This script activates the virtual environment and runs the main program

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Virtual environment not found!"
    echo "Please run setup.sh first:"
    echo "  sudo bash setup.sh"
    exit 1
fi

# Activate virtual environment and run
cd "$SCRIPT_DIR"
./venv/bin/python main.py "$@"