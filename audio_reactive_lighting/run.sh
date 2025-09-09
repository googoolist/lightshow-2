#!/bin/bash

# Run script for Audio-Reactive DMX Lighting System
# This script activates the virtual environment and runs the main program

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/startup.log"

# Log startup attempt
echo "$(date): Starting Audio DMX Controller" >> "$LOG_FILE"

# Wait for display to be ready (important for auto-start)
export DISPLAY=:0
export XAUTHORITY=$HOME/.Xauthority

# Wait for desktop to be ready
sleep 5

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "$(date): Virtual environment not found!" >> "$LOG_FILE"
    echo "Virtual environment not found!"
    echo "Please run install_user.sh first"
    exit 1
fi

# Wait for OLA to be ready
echo "$(date): Waiting for OLA..." >> "$LOG_FILE"
while ! nc -z localhost 9090 2>/dev/null; do
    sleep 1
done
echo "$(date): OLA is ready" >> "$LOG_FILE"

# Activate virtual environment and run
cd "$SCRIPT_DIR"
echo "$(date): Starting main.py" >> "$LOG_FILE"
./venv/bin/python main.py "$@" 2>&1 | tee -a "$LOG_FILE"