#!/bin/bash

# ============================================================================
# Audio-Reactive DMX Lighting System - Uninstall Script
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo ~$INSTALL_USER)

echo -e "${RED}============================================${NC}"
echo -e "${RED}Audio-Reactive DMX - Uninstaller${NC}"
echo -e "${RED}============================================${NC}"
echo ""
echo "This will remove:"
echo "  - Auto-start configuration"
echo "  - Python virtual environment"
echo "  - System service files"
echo ""
echo "This will NOT remove:"
echo "  - System packages (Python, OLA, etc.)"
echo "  - Your configuration files"
echo "  - Log files"
echo ""
read -p "Continue with uninstall? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled"
    exit 0
fi

# Stop any running instances
echo -e "${YELLOW}Stopping application...${NC}"
killall python 2>/dev/null || true

# Remove autostart
echo -e "${YELLOW}Removing autostart...${NC}"
rm -f "$USER_HOME/.config/autostart/audio_dmx.desktop"

# Remove systemd service if it exists
if [ -f /etc/systemd/system/audio_dmx.service ]; then
    echo -e "${YELLOW}Removing systemd service...${NC}"
    sudo systemctl stop audio_dmx.service 2>/dev/null || true
    sudo systemctl disable audio_dmx.service 2>/dev/null || true
    sudo rm -f /etc/systemd/system/audio_dmx.service
    sudo systemctl daemon-reload
fi

# Remove virtual environment
echo -e "${YELLOW}Removing virtual environment...${NC}"
rm -rf "$INSTALL_DIR/venv"

# Remove udev rules
if [ -f /etc/udev/rules.d/99-dmx.rules ]; then
    echo -e "${YELLOW}Removing udev rules...${NC}"
    sudo rm -f /etc/udev/rules.d/99-dmx.rules
    sudo udevadm control --reload-rules
fi

echo ""
echo -e "${GREEN}Uninstall complete!${NC}"
echo ""
echo "Kept files:"
echo "  - Configuration: $INSTALL_DIR/config.py"
echo "  - Logs: $INSTALL_DIR/*.log"
echo "  - Source code: $INSTALL_DIR/*.py"
echo ""
echo "To completely remove everything:"
echo "  rm -rf $INSTALL_DIR"
echo ""
echo "To remove system packages (optional):"
echo "  sudo apt-get remove ola ola-python"
echo ""