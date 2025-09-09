#!/bin/bash

# Script to configure Raspberry Pi for auto-start on boot
# Run with: sudo bash setup_autostart.sh

echo "=========================================="
echo "Configuring Auto-Start on Boot"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Detect user
if [ -n "$SUDO_USER" ]; then
    INSTALL_USER="$SUDO_USER"
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    echo "Error: Cannot detect user. Please run with sudo."
    exit 1
fi

echo "Configuring for user: $INSTALL_USER"
echo ""

# Step 1: Enable OLA to start on boot
echo "1. Enabling OLA daemon auto-start..."
systemctl enable olad
systemctl start olad
echo "   ✓ OLA daemon configured"

# Step 2: Update the systemd service with longer delay
echo ""
echo "2. Updating systemd service for proper startup sequence..."
cat > /etc/systemd/system/audio_dmx.service << EOF
[Unit]
Description=Audio-Reactive DMX Lighting Controller
After=graphical.target olad.service sound.target
Wants=olad.service
Requires=graphical.target

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_USER
Environment="DISPLAY=:0"
Environment="XAUTHORITY=$USER_HOME/.Xauthority"
Environment="HOME=$USER_HOME"
Environment="XDG_RUNTIME_DIR=/run/user/$(id -u $INSTALL_USER)"
WorkingDirectory=$USER_HOME/audio_reactive_lighting

# Wait for system to fully boot
ExecStartPre=/bin/sleep 10
# Ensure OLA is ready
ExecStartPre=/bin/bash -c 'until nc -z localhost 9090; do sleep 1; done'
# Start the application
ExecStart=$USER_HOME/audio_reactive_lighting/venv/bin/python $USER_HOME/audio_reactive_lighting/main.py

Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

systemctl daemon-reload
echo "   ✓ Systemd service updated"

# Step 3: Enable the service
echo ""
echo "3. Enabling audio_dmx service..."
systemctl enable audio_dmx.service
echo "   ✓ Service will start on boot"

# Step 4: Configure auto-login (Raspberry Pi OS)
echo ""
echo "4. Configuring auto-login to desktop..."
if [ -f /etc/lightdm/lightdm.conf ]; then
    # Backup original
    cp /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.backup
    
    # Enable auto-login
    sed -i "s/^#autologin-user=.*/autologin-user=$INSTALL_USER/" /etc/lightdm/lightdm.conf
    sed -i "s/^autologin-user=.*/autologin-user=$INSTALL_USER/" /etc/lightdm/lightdm.conf
    
    # If the line doesn't exist, add it
    if ! grep -q "autologin-user=" /etc/lightdm/lightdm.conf; then
        sed -i '/\[Seat:\*\]/a autologin-user='$INSTALL_USER /etc/lightdm/lightdm.conf
    fi
    
    echo "   ✓ Auto-login configured for $INSTALL_USER"
else
    echo "   ⚠ lightdm.conf not found. Please configure auto-login manually:"
    echo "     Run: sudo raspi-config"
    echo "     Go to: System Options > Boot / Auto Login > Desktop Autologin"
fi

# Step 5: Disable screen blanking
echo ""
echo "5. Disabling screen blanking and power management..."
# For console
echo "consoleblank=0" >> /boot/cmdline.txt 2>/dev/null

# For X11
if [ ! -f /etc/X11/xorg.conf.d/10-blanking.conf ]; then
    mkdir -p /etc/X11/xorg.conf.d
    cat > /etc/X11/xorg.conf.d/10-blanking.conf << EOF
Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
EndSection
EOF
fi

# For lightdm
if [ -f /etc/lightdm/lightdm.conf ]; then
    if ! grep -q "xserver-command=" /etc/lightdm/lightdm.conf; then
        sed -i '/\[Seat:\*\]/a xserver-command=X -s 0 -dpms' /etc/lightdm/lightdm.conf
    fi
fi

echo "   ✓ Screen blanking disabled"

echo ""
echo "=========================================="
echo "Auto-start configuration complete!"
echo "=========================================="
echo ""
echo "The system will now:"
echo "1. Auto-login to desktop as $INSTALL_USER"
echo "2. Start OLA daemon automatically"
echo "3. Wait for system to be ready"
echo "4. Launch the DMX lighting GUI in fullscreen"
echo ""
echo "Controls in fullscreen mode:"
echo "- Press ESC to exit the application"
echo "- Click mode buttons to change lighting effects"
echo ""
echo "To test without rebooting:"
echo "  sudo systemctl start audio_dmx.service"
echo ""
echo "To check service status:"
echo "  systemctl status audio_dmx.service"
echo ""
echo "To view logs:"
echo "  journalctl -u audio_dmx.service -f"
echo ""
echo "Ready to reboot? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Rebooting in 5 seconds..."
    sleep 5
    reboot
else
    echo "Reboot when ready with: sudo reboot"
fi