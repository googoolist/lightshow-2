#!/bin/bash

# Setup script for Audio-Reactive DMX Lighting System on Raspberry Pi
# Run with: sudo bash setup.sh

echo "Audio-Reactive DMX Lighting System Setup"
echo "========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Detect the actual user who invoked sudo (or current user if not using sudo)
if [ -n "$SUDO_USER" ]; then
    INSTALL_USER="$SUDO_USER"
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    # If not running with sudo, try to detect a regular user
    INSTALL_USER="${USER:-$(whoami)}"
    USER_HOME="${HOME:-/home/$INSTALL_USER}"
fi

echo "Installing for user: $INSTALL_USER"
echo "Home directory: $USER_HOME"

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
apt-get install -y python3-pip python3-tk python3-dev python3-venv portaudio19-dev

# Install OLA (Open Lighting Architecture)
echo "Installing OLA..."
apt-get install -y ola ola-python

# Copy files to home directory
echo "Copying application files..."
TARGET_DIR="$USER_HOME/audio_reactive_lighting"
mkdir -p "$TARGET_DIR"
cp -r ./*.py "$TARGET_DIR/"
cp audio_dmx.service "$TARGET_DIR/"
cp setup.sh "$TARGET_DIR/"
cp run.sh "$TARGET_DIR/"
cp README.md "$TARGET_DIR/" 2>/dev/null || true

# Create virtual environment
echo "Creating Python virtual environment..."
cd "$TARGET_DIR"
sudo -u "$INSTALL_USER" python3 -m venv venv

# Install Python dependencies in virtual environment
echo "Installing Python dependencies..."
sudo -u "$INSTALL_USER" "$TARGET_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$INSTALL_USER" "$TARGET_DIR/venv/bin/pip" install numpy sounddevice aubio

# Set ownership
chown -R "$INSTALL_USER:$INSTALL_USER" "$TARGET_DIR"
chmod +x "$TARGET_DIR/main.py"
chmod +x "$TARGET_DIR/run.sh"

# Create customized systemd service file
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

systemctl daemon-reload
systemctl enable audio_dmx.service

# Configure OLA
echo "Configuring OLA..."
systemctl enable olad
systemctl start olad

echo ""
echo "Setup complete!"
echo ""
echo "IMPORTANT: Manual configuration required:"
echo "1. Configure your DMX USB dongle in OLA:"
echo "   - Open web browser and go to: http://localhost:9090"
echo "   - Add your DMX USB device"
echo "   - Patch it to Universe 1"
echo ""
echo "2. Configure your system for auto-login (if using GUI mode):"
echo "   - For Raspberry Pi: sudo raspi-config"
echo "     Go to: System Options > Boot / Auto Login > Desktop Autologin"
echo "   - For Ubuntu: Settings > Users > Automatic Login"
echo ""
echo "3. Adjust PAR light channel mappings in:"
echo "   $TARGET_DIR/config.py"
echo ""
echo "4. Test the system:"
echo "   cd $TARGET_DIR"
echo "   ./venv/bin/python main.py"
echo ""
echo "5. Reboot to start automatically:"
echo "   sudo reboot"