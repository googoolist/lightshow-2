#!/bin/bash

# ============================================================================
# Audio-Reactive DMX Lighting System - Complete Installation Script
# ============================================================================
# This script handles the complete installation on a fresh Raspberry Pi
# Run with: bash install.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation directory (where this script is located)
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo ~$INSTALL_USER)

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Audio-Reactive DMX Lighting System Installer${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo "Installing for user: $INSTALL_USER"
echo "User home: $USER_HOME"
echo ""

# Function to check if running with sudo when needed
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}This step requires sudo privileges.${NC}"
        echo "Re-running with sudo..."
        sudo bash "$0" "$@"
        exit $?
    fi
}

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[i]${NC} $1"
}

# ============================================================================
# STEP 1: System Dependencies
# ============================================================================
install_system_deps() {
    echo ""
    echo -e "${GREEN}Step 1: Installing System Dependencies${NC}"
    echo "======================================="
    
    # Check if we need sudo
    if [ "$EUID" -ne 0 ]; then
        print_info "Switching to sudo for system packages..."
        sudo bash -c "$(declare -f install_system_deps_sudo); install_system_deps_sudo"
    else
        install_system_deps_sudo
    fi
}

install_system_deps_sudo() {
    # Update package list
    print_info "Updating package lists..."
    apt-get update
    
    # Install Python and development tools
    print_info "Installing Python and development tools..."
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-tk \
        build-essential \
        git
    
    # Install audio dependencies
    print_info "Installing audio dependencies..."
    apt-get install -y \
        portaudio19-dev \
        libasound2-dev \
        libatlas-base-dev
    
    # Install OLA (Open Lighting Architecture)
    print_info "Installing OLA..."
    apt-get install -y ola ola-python
    
    # Install additional utilities
    print_info "Installing utilities..."
    apt-get install -y \
        netcat \
        libftdi1 \
        screen
    
    print_status "System dependencies installed"
}

# ============================================================================
# STEP 2: Python Virtual Environment
# ============================================================================
setup_python_env() {
    echo ""
    echo -e "${GREEN}Step 2: Setting Up Python Environment${NC}"
    echo "======================================"
    
    cd "$INSTALL_DIR"
    
    # Remove old venv if it exists
    if [ -d "venv" ]; then
        print_info "Removing old virtual environment..."
        rm -rf venv
    fi
    
    # Create virtual environment
    print_info "Creating virtual environment..."
    python3 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip wheel
    
    # Install Python packages
    print_info "Installing Python packages..."
    pip install numpy
    pip install sounddevice
    pip install aubio
    pip install "protobuf>=3.20.0,<4.0.0"
    
    # Link OLA Python bindings
    print_info "Linking OLA Python bindings..."
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    OLA_PATHS=(
        "/usr/lib/python$PYTHON_VERSION/dist-packages/ola"
        "/usr/lib/python3/dist-packages/ola"
        "/usr/local/lib/python$PYTHON_VERSION/dist-packages/ola"
    )
    
    for ola_path in "${OLA_PATHS[@]}"; do
        if [ -d "$ola_path" ]; then
            ln -sfn "$ola_path" "venv/lib/python$PYTHON_VERSION/site-packages/ola"
            print_status "OLA Python bindings linked"
            break
        fi
    done
    
    deactivate
    print_status "Python environment setup complete"
}

# ============================================================================
# STEP 3: OLA Configuration
# ============================================================================
configure_ola() {
    echo ""
    echo -e "${GREEN}Step 3: Configuring OLA${NC}"
    echo "======================="
    
    if [ "$EUID" -ne 0 ]; then
        sudo bash -c "$(declare -f configure_ola_sudo); configure_ola_sudo"
    else
        configure_ola_sudo
    fi
}

configure_ola_sudo() {
    # Enable and start OLA daemon
    print_info "Enabling OLA daemon..."
    systemctl enable olad
    systemctl start olad
    
    # Wait for OLA to start
    print_info "Waiting for OLA to start..."
    sleep 3
    
    # Configure FTDI plugin for USB DMX devices
    if [ -f /etc/ola/ola-ftdidmx.conf ]; then
        print_info "Configuring FTDI DMX plugin..."
        sed -i 's/enabled = .*/enabled = true/' /etc/ola/ola-ftdidmx.conf
    fi
    
    # Disable conflicting plugins
    if [ -f /etc/ola/ola-usbserial.conf ]; then
        sed -i 's/enabled = .*/enabled = false/' /etc/ola/ola-usbserial.conf
    fi
    
    # Add user to dialout group for USB access
    print_info "Adding user to dialout group..."
    usermod -a -G dialout $INSTALL_USER
    
    # Create udev rule for FTDI devices
    print_info "Creating udev rules for DMX devices..."
    cat > /etc/udev/rules.d/99-dmx.rules << 'EOF'
# FTDI USB DMX devices
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", MODE="0666", GROUP="dialout"
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6015", MODE="0666", GROUP="dialout"
EOF
    
    udevadm control --reload-rules
    udevadm trigger
    
    # Restart OLA to apply changes
    systemctl restart olad
    
    print_status "OLA configured"
}

# ============================================================================
# STEP 4: Auto-start Configuration
# ============================================================================
setup_autostart() {
    echo ""
    echo -e "${GREEN}Step 4: Configuring Auto-start${NC}"
    echo "=============================="
    
    # Create autostart script with correct paths
    print_info "Creating autostart script..."
    cat > "$INSTALL_DIR/autostart.sh" << EOF
#!/bin/bash

# Auto-start script for Audio-Reactive DMX Lighting System
export DISPLAY=:0
export XAUTHORITY=\$HOME/.Xauthority

# Change to application directory
cd "$INSTALL_DIR"

# Log file
LOG="$INSTALL_DIR/autostart.log"

echo "=======================" >> "\$LOG"
echo "\$(date): Starting..." >> "\$LOG"

# Wait for desktop
sleep 10

# Check for OLA
if ! systemctl is-active --quiet olad; then
    echo "\$(date): Starting OLA" >> "\$LOG"
    sudo systemctl start olad
    sleep 5
fi

# Wait for OLA to be ready
while ! nc -z localhost 9090 2>/dev/null; do
    echo "\$(date): Waiting for OLA..." >> "\$LOG"
    sleep 1
done

echo "\$(date): Starting application" >> "\$LOG"

# Run the application
./venv/bin/python main.py >> "\$LOG" 2>&1 &

echo "\$(date): Started with PID \$!" >> "\$LOG"
EOF
    
    chmod +x "$INSTALL_DIR/autostart.sh"
    
    # Create desktop autostart entry
    print_info "Creating desktop autostart entry..."
    mkdir -p "$USER_HOME/.config/autostart"
    cat > "$USER_HOME/.config/autostart/audio_dmx.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Audio DMX Controller
Exec=$INSTALL_DIR/autostart.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Terminal=false
Comment=Audio-Reactive DMX Lighting System
Icon=applications-multimedia
EOF
    
    # Set ownership
    chown -R $INSTALL_USER:$INSTALL_USER "$USER_HOME/.config/autostart"
    
    print_status "Auto-start configured"
}

# ============================================================================
# STEP 5: System Optimizations
# ============================================================================
optimize_system() {
    echo ""
    echo -e "${GREEN}Step 5: System Optimizations${NC}"
    echo "============================"
    
    if [ "$EUID" -ne 0 ]; then
        sudo bash -c "$(declare -f optimize_system_sudo); optimize_system_sudo"
    else
        optimize_system_sudo
    fi
}

optimize_system_sudo() {
    # Disable screen blanking
    print_info "Disabling screen blanking..."
    
    # For console
    if ! grep -q "consoleblank=0" /boot/cmdline.txt 2>/dev/null; then
        sed -i 's/$/ consoleblank=0/' /boot/cmdline.txt
    fi
    
    # For X11
    mkdir -p /etc/X11/xorg.conf.d
    cat > /etc/X11/xorg.conf.d/10-blanking.conf << 'EOF'
Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
    Option "DPMS" "false"
EndSection
EOF
    
    # Configure auto-login (for Raspberry Pi OS with lightdm)
    if [ -f /etc/lightdm/lightdm.conf ]; then
        print_info "Configuring auto-login..."
        sed -i "s/^#autologin-user=.*/autologin-user=$INSTALL_USER/" /etc/lightdm/lightdm.conf
        sed -i "s/^autologin-user=.*/autologin-user=$INSTALL_USER/" /etc/lightdm/lightdm.conf
        
        if ! grep -q "autologin-user=" /etc/lightdm/lightdm.conf; then
            sed -i "/\[Seat:\*\]/a autologin-user=$INSTALL_USER" /etc/lightdm/lightdm.conf
        fi
    fi
    
    print_status "System optimizations complete"
}

# ============================================================================
# STEP 6: Test Installation
# ============================================================================
test_installation() {
    echo ""
    echo -e "${GREEN}Step 6: Testing Installation${NC}"
    echo "============================"
    
    cd "$INSTALL_DIR"
    
    # Test Python environment
    print_info "Testing Python environment..."
    if ./venv/bin/python -c "import numpy, sounddevice, aubio; print('Python packages OK')" 2>/dev/null; then
        print_status "Python packages OK"
    else
        print_error "Python packages test failed"
    fi
    
    # Test OLA
    print_info "Testing OLA connection..."
    if ./venv/bin/python -c "from ola.ClientWrapper import ClientWrapper; print('OLA bindings OK')" 2>/dev/null; then
        print_status "OLA bindings OK"
    else
        print_error "OLA bindings test failed"
    fi
    
    # Test GUI
    print_info "Testing GUI libraries..."
    if ./venv/bin/python -c "import tkinter; print('Tkinter OK')" 2>/dev/null; then
        print_status "Tkinter OK"
    else
        print_error "Tkinter test failed"
    fi
    
    # Check if OLA daemon is running
    if systemctl is-active --quiet olad; then
        print_status "OLA daemon is running"
    else
        print_error "OLA daemon is not running"
    fi
}

# ============================================================================
# MAIN INSTALLATION FLOW
# ============================================================================

# Check if we're in the right directory
if [ ! -f "$INSTALL_DIR/main.py" ]; then
    print_error "main.py not found in current directory!"
    print_error "Please run this script from the app directory"
    exit 1
fi

echo ""
print_info "This installer will:"
echo "  1. Install system dependencies (requires sudo)"
echo "  2. Setup Python virtual environment"
echo "  3. Configure OLA for DMX"
echo "  4. Setup auto-start on boot"
echo "  5. Optimize system settings"
echo "  6. Test the installation"
echo ""
read -p "Continue with installation? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled"
    exit 0
fi

# Run installation steps
install_system_deps
setup_python_env
configure_ola
setup_autostart
optimize_system
test_installation

# ============================================================================
# COMPLETION
# ============================================================================

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your DMX interface:"
echo "   Open browser: http://localhost:9090"
echo "   - Add your DMX USB device"
echo "   - Patch to Universe 1"
echo ""
echo "2. Test the application:"
echo "   cd $INSTALL_DIR"
echo "   ./venv/bin/python main.py"
echo ""
echo "3. The system will auto-start on next boot"
echo ""
echo "4. To start now without rebooting:"
echo "   $INSTALL_DIR/autostart.sh"
echo ""
echo "Controls:"
echo "  - ESC or Q: Exit application"
echo "  - Mode buttons: Switch lighting effects"
echo "  - Smoothness slider: Adjust transition speed"
echo ""
print_info "You may need to logout and login for group permissions to take effect"
print_info "Or reboot with: sudo reboot"
echo ""