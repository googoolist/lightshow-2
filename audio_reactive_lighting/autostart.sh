#!/bin/bash

# Simple autostart script with error handling
# This runs from the desktop autostart

# Set display
export DISPLAY=:0
export XAUTHORITY=$HOME/.Xauthority

# Change to the app directory (CORRECT PATH)
cd /home/$USER/lightshow-2/audio_reactive_lighting

# Log file
LOG="/home/$USER/lightshow-2/audio_reactive_lighting/autostart.log"

# Log startup
echo "========================" >> "$LOG"
echo "$(date): Autostart beginning" >> "$LOG"

# Wait for desktop to be fully loaded
sleep 10
echo "$(date): Desktop wait complete" >> "$LOG"

# Check if OLA is running
if ! systemctl is-active --quiet olad; then
    echo "$(date): Starting OLA daemon" >> "$LOG"
    sudo systemctl start olad
    sleep 5
fi

# Check if we can connect to display
if ! xset q &>/dev/null; then
    echo "$(date): ERROR - Cannot connect to display" >> "$LOG"
    exit 1
fi

echo "$(date): Display connected" >> "$LOG"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "$(date): ERROR - Virtual environment not found" >> "$LOG"
    exit 1
fi

echo "$(date): Starting application" >> "$LOG"

# Run the application
./venv/bin/python main.py >> "$LOG" 2>&1 &

echo "$(date): Application launched with PID $!" >> "$LOG"