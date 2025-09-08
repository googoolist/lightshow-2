#!/bin/bash

# System-level setup script (requires sudo)
# This handles system packages and service installation

echo "Audio-Reactive DMX Lighting System - System Setup"
echo "================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script must be run with sudo"
    echo "Usage: sudo bash setup_system.sh"
    exit 1
fi

# Detect the actual user who invoked sudo
if [ -n "$SUDO_USER" ]; then
    INSTALL_USER="$SUDO_USER"
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    echo "Error: Cannot detect user. Please run with sudo."
    exit 1
fi

echo "Setting up for user: $INSTALL_USER"
echo "Installation directory: $USER_HOME/audio_reactive_lighting"

# Get the current directory
CURRENT_DIR="$(pwd)"
TARGET_DIR="$USER_HOME/audio_reactive_lighting"

# Update system
echo ""
echo "Installing system packages..."
apt-get update
apt-get install -y python3 python3-pip python3-venv python3-tk python3-dev portaudio19-dev

# Install OLA
echo ""
echo "Installing OLA (Open Lighting Architecture)..."
apt-get install -y ola ola-python

# Enable OLA service
systemctl enable olad
systemctl start olad

# Create systemd service file
echo ""
echo "Creating systemd service..."
cat > /etc/systemd/system/audio_dmx.service << EOF
[Unit]
Description=Audio-Reactive DMX Lighting Controller
After=graphical.target olad.service
Wants=olad.service

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_USER
Environment="DISPLAY=:0.0"
Environment="XAUTHORITY=$USER_HOME/.Xauthority"
Environment="HOME=$USER_HOME"
WorkingDirectory=$TARGET_DIR
ExecStartPre=/bin/sleep 5
ExecStart=$TARGET_DIR/venv/bin/python $TARGET_DIR/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical.target
EOF

# Reload systemd
systemctl daemon-reload

echo ""
echo "=========================================="
echo "System setup complete!"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure OLA for your DMX adapter:"
echo "   http://localhost:9090"
echo "   - Add your DMX USB device"
echo "   - Patch it to Universe 1"
echo ""
echo "2. Run the user installation script (as regular user, not sudo):"
echo "   cd $CURRENT_DIR"
echo "   ./install_user.sh"
echo ""
echo "3. Configure auto-login if desired:"
echo "   - Raspberry Pi: sudo raspi-config"
echo "   - Ubuntu: Settings > Users > Automatic Login"
echo ""
echo "4. To enable auto-start on boot (after user install):"
echo "   sudo systemctl enable audio_dmx.service"
echo ""
echo "5. To start the service now:"
echo "   sudo systemctl start audio_dmx.service"