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
TARGET_DIR="/home/pi/audio_reactive_lighting"
mkdir -p "$TARGET_DIR"
cp -r ./*.py "$TARGET_DIR/"
cp audio_dmx.service "$TARGET_DIR/"
cp setup.sh "$TARGET_DIR/"
cp README.md "$TARGET_DIR/" 2>/dev/null || true

# Create virtual environment
echo "Creating Python virtual environment..."
cd "$TARGET_DIR"
sudo -u pi python3 -m venv venv

# Install Python dependencies in virtual environment
echo "Installing Python dependencies..."
sudo -u pi "$TARGET_DIR/venv/bin/pip" install --upgrade pip
sudo -u pi "$TARGET_DIR/venv/bin/pip" install numpy sounddevice aubio

# Set ownership
chown -R pi:pi "$TARGET_DIR"
chmod +x "$TARGET_DIR/main.py"

# Install systemd service
echo "Installing systemd service..."
cp audio_dmx.service /etc/systemd/system/
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
echo "2. Configure Raspberry Pi for auto-login:"
echo "   - Run: sudo raspi-config"
echo "   - Go to: System Options > Boot / Auto Login"
echo "   - Select: Desktop Autologin"
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