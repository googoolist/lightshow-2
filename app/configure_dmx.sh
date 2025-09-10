#!/bin/bash

# Post-reboot DMX configuration script
# Run this after reboot to ensure FTDI is properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}DMX Configuration Helper${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""

# Check if FTDI device is present
echo -e "${YELLOW}[i]${NC} Checking for FTDI device..."
if lsusb | grep -q "0403:600"; then
    echo -e "${GREEN}[✓]${NC} FTDI device found"
else
    echo -e "${RED}[✗]${NC} FTDI device not found. Please check USB connection."
    exit 1
fi

# Check if ftdi_sio module is loaded (it shouldn't be)
if lsmod | grep -q ftdi_sio; then
    echo -e "${YELLOW}[i]${NC} FTDI serial driver is loaded. Attempting to remove..."
    sudo modprobe -r ftdi_sio 2>/dev/null || {
        echo -e "${RED}[✗]${NC} Could not remove ftdi_sio module"
        echo "Please reboot or manually stop any process using /dev/ttyUSB0"
        exit 1
    }
    echo -e "${GREEN}[✓]${NC} FTDI serial driver removed"
fi

# Ensure OLA is running
echo -e "${YELLOW}[i]${NC} Checking OLA daemon..."
if ! systemctl is-active --quiet olad; then
    echo -e "${YELLOW}[i]${NC} Starting OLA daemon..."
    sudo systemctl start olad
    sleep 5
fi
echo -e "${GREEN}[✓]${NC} OLA daemon is running"

# Wait for OLA to be ready
echo -e "${YELLOW}[i]${NC} Waiting for OLA to be ready..."
while ! nc -z localhost 9090 2>/dev/null; do
    sleep 1
done
echo -e "${GREEN}[✓]${NC} OLA is ready"

# Configure plugins
echo -e "${YELLOW}[i]${NC} Configuring OLA plugins..."

# First, stop OLA to ensure clean state
echo -e "${YELLOW}[i]${NC} Stopping OLA for plugin configuration..."
sudo systemctl stop olad
sleep 2

# Disable ALL conflicting plugins via config files
echo -e "${YELLOW}[i]${NC} Disabling conflicting plugins in config files..."
sudo sed -i 's/enabled = .*/enabled = false/' /etc/ola/ola-opendmx.conf 2>/dev/null || true
sudo sed -i 's/enabled = .*/enabled = false/' /etc/ola/ola-usbserial.conf 2>/dev/null || true
sudo sed -i 's/enabled = .*/enabled = true/' /etc/ola/ola-ftdidmx.conf 2>/dev/null || true

# Start OLA again
echo -e "${YELLOW}[i]${NC} Starting OLA..."
sudo systemctl start olad
sleep 5

# Wait for OLA to be ready
while ! nc -z localhost 9090 2>/dev/null; do
    sleep 1
done

# Now use CLI to ensure plugins are set correctly
echo -e "${YELLOW}[i]${NC} Setting plugin states via CLI..."

# Disable conflicting plugins (multiple attempts to ensure it takes)
for i in {1..3}; do
    ola_plugin_state --plugin-id 5 --state disable 2>/dev/null || true  # Enttec Open DMX
    sleep 1
done

for i in {1..3}; do
    ola_plugin_state --plugin-id 7 --state disable 2>/dev/null || true  # Serial USB
    sleep 1
done

# Enable FTDI plugin
for i in {1..3}; do
    ola_plugin_state --plugin-id 13 --state enable 2>/dev/null && break
    sleep 1
done

# Check if FTDI is actually enabled
if ! ola_plugin_info | grep -A1 "Plugin 13" | grep -q "active: 1"; then
    echo -e "${RED}[✗]${NC} FTDI plugin is not active"
    
    # Try one more time with full restart
    echo -e "${YELLOW}[i]${NC} Attempting force configuration..."
    sudo systemctl stop olad
    
    # Directly edit the preferences file if it exists
    if [ -f ~/.ola/ola-universe.conf ]; then
        sed -i '/^5-/d' ~/.ola/ola-universe.conf  # Remove Enttec Open DMX entries
    fi
    
    sudo systemctl start olad
    sleep 5
    
    ola_plugin_state --plugin-id 13 --state enable || {
        echo -e "${RED}[✗]${NC} Failed to enable FTDI plugin"
        echo "Manual intervention required. Please check:"
        echo "  1. USB device is connected"
        echo "  2. No other process is using the device"
        echo "  3. ftdi_sio module is not loaded (lsmod | grep ftdi)"
        exit 1
    }
fi

echo -e "${GREEN}[✓]${NC} Plugin configuration complete"

# Final restart to ensure everything is applied
echo -e "${YELLOW}[i]${NC} Final OLA restart..."
sudo systemctl restart olad
sleep 5

# Wait for OLA to be ready again
while ! nc -z localhost 9090 2>/dev/null; do
    sleep 1
done

# Configure universe patching
echo -e "${YELLOW}[i]${NC} Patching FTDI device to Universe 1..."

# List available devices
echo -e "${YELLOW}[i]${NC} Available devices:"
ola_dev_info

# Try to patch FTDI device to universe 1
ola_patch --device 13 --port 0 --universe 1 2>/dev/null || {
    echo -e "${YELLOW}[!]${NC} Could not auto-patch. Please use web interface:"
    echo "    http://localhost:9090"
    echo "    1. Go to 'Add/Remove Universes'"
    echo "    2. Add Universe 1"
    echo "    3. Go to 'Patch' tab"
    echo "    4. Connect FTDI USB DMX output to Universe 1"
}

# Verify configuration
echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}Configuration Summary:${NC}"
echo -e "${GREEN}==================================${NC}"

# Show plugin status
echo -e "${YELLOW}Plugin Status:${NC}"
ola_plugin_info | grep -E "Plugin [0-9]+|FTDI|Serial|Enttec" | while read line; do
    if echo "$line" | grep -q "Plugin"; then
        echo ""
        echo "$line"
    else
        echo "  $line"
    fi
done

echo ""
echo -e "${YELLOW}Universe Configuration:${NC}"
ola_universe_list

echo ""
echo -e "${GREEN}[✓]${NC} DMX configuration complete!"
echo ""
echo "You can now:"
echo "  1. Test with: ola_dmxconsole -u 1"
echo "  2. Run the application: cd ~/lightshow-2/app && ./venv/bin/python main.py"
echo "  3. Access OLA web interface: http://localhost:9090"