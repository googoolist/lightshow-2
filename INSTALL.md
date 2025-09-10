# Installation Guide

## Quick Install (Fresh Raspberry Pi)

1. **Clone or copy the project to your Raspberry Pi:**
```bash
cd ~
git clone [your-repo-url] lightshow-2
cd lightshow-2/app
```

2. **Run the installer:**
```bash
bash install.sh
```

The installer will:
- Install all system dependencies
- Create Python virtual environment
- Configure OLA for DMX
- Setup auto-start on boot
- Optimize system settings
- Test the installation

3. **Configure your DMX adapter:**
- Open browser: http://localhost:9090
- Add your USB DMX device
- Patch it to Universe 1

4. **Reboot to start automatically:**
```bash
sudo reboot
```

## Manual Testing

Test without rebooting:
```bash
cd ~/lightshow-2/app
./venv/bin/python main.py
```

## Troubleshooting

### Check logs:
```bash
# Auto-start log
cat ~/lightshow-2/app/autostart.log

# Application log  
cat ~/lightshow-2/app/startup.log
```

### Check services:
```bash
# OLA status
systemctl status olad

# Application status (if using systemd)
systemctl status audio_dmx
```

### Manual start:
```bash
cd ~/lightshow-2/app
./autostart.sh
```

## Controls

- **ESC or Q**: Exit application
- **Mode Buttons**: Switch between Smooth, Rapid, and Classic modes
- **Smoothness Slider**: Adjust transition speed (left=fast, right=smooth)

## Configuration

Edit `config.py` to:
- Adjust DMX channel mappings for your PAR lights
- Change colors and patterns
- Toggle fullscreen mode
- Adjust audio sensitivity

## Uninstall

To remove the application:
```bash
cd ~/lightshow-2/app
bash uninstall.sh
```

## Requirements

- Raspberry Pi 3B or newer
- Raspberry Pi OS with Desktop
- USB Audio input device
- USB DMX adapter (FTDI-based)
- DMX PAR lights

## Default Settings

- **DMX Universe**: 1
- **PAR 1**: DMX channels 1-8
- **PAR 2**: DMX channels 9-16  
- **PAR 3**: DMX channels 17-24
- **Window Mode**: Windowed (change FULLSCREEN in config.py)
- **Default Mode**: Classic