# Audio-Reactive DMX Lighting System

A real-time audio-reactive lighting controller for Raspberry Pi that analyzes live audio input and controls DMX PAR lights synchronized to the music's beat, tempo, and intensity.

## Features

- **Real-time Beat Detection**: Detects beats and estimates BPM using advanced audio analysis
- **3 PAR Light Control**: Configured for three DMX PAR lights with customizable channel mappings
- **Multiple Lighting Modes**:
  - Beat-synchronized color cycling
  - Alternating light patterns
  - Intensity-based brightness modulation
  - Flash effects on beat detection
- **Graphical Interface**: Tkinter-based GUI showing BPM, intensity, and audio status
- **Auto-start on Boot**: Systemd service for kiosk-mode operation

## Hardware Requirements

- Raspberry Pi 3B or newer
- USB audio interface or microphone (mono input)
- USB-to-DMX adapter (Enttec Open DMX or FTDI-based)
- 3 DMX PAR lights
- DMX cables

## Software Requirements

- Raspberry Pi OS (with desktop)
- Python 3.7+
- OLA (Open Lighting Architecture)
- Required Python packages: numpy, sounddevice, aubio

## Installation

### Quick Setup

1. Clone or copy the project to your Raspberry Pi:
```bash
cd ~
git clone <repository-url> audio_reactive_lighting
cd audio_reactive_lighting
```

2. Run the setup script:
```bash
sudo bash setup.sh
```

3. Configure OLA for your DMX adapter:
   - Open browser: http://localhost:9090
   - Add your DMX USB device
   - Patch it to Universe 1

4. Edit `config.py` to match your PAR light DMX channel mappings

5. Test the system:
```bash
python3 main.py
```

### Manual Installation

1. Install system dependencies:
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-tk python3-dev portaudio19-dev
sudo apt-get install -y ola ola-python
```

2. Install Python packages:
```bash
pip3 install numpy sounddevice aubio
```

3. Configure and start OLA daemon:
```bash
sudo systemctl enable olad
sudo systemctl start olad
```

## Configuration

Edit `config.py` to customize:

### PAR Light Channel Mappings
```python
LIGHT_FIXTURES = [
    {
        "name": "PAR1",
        "start_channel": 1,
        "channels": {
            "dimmer": 0,    # Channel offset from start_channel
            "red": 1,
            "green": 2,
            "blue": 3,
            # Add/remove channels based on your PAR model
        }
    },
    # Configure PAR2 and PAR3...
]
```

### Audio Settings
- `SAMPLE_RATE`: Audio sampling rate (default: 44100 Hz)
- `BUFFER_SIZE`: Audio buffer size (default: 512 samples)
- `SILENCE_THRESHOLD`: RMS level for silence detection

### Lighting Behavior
- `COLOR_PRESETS`: List of RGB colors to cycle through
- `ALTERNATING_MODE`: Enable/disable alternating light patterns
- `COLOR_CYCLE_ON_BEAT`: Cycle colors on each beat
- `BRIGHTNESS_BASE`: Overall brightness scaling (0.0-1.0)

## Usage

### Running Manually

After installation, use the run script or activate the virtual environment:

```bash
cd ~/audio_reactive_lighting

# Option 1: Use the run script
./run.sh

# Option 2: Activate virtual environment manually
source venv/bin/activate
python main.py

# For headless mode (no GUI):
./run.sh --headless

# Check dependencies:
./run.sh --check-deps
```

### Auto-start on Boot

1. Enable auto-login to desktop:
```bash
sudo raspi-config
# System Options > Boot / Auto Login > Desktop Autologin
```

2. Enable the systemd service:
```bash
sudo systemctl enable audio_dmx.service
sudo systemctl start audio_dmx.service
```

3. Check service status:
```bash
systemctl status audio_dmx.service
```

## Troubleshooting

### No Audio Input Detected
- Check USB audio device is connected
- List audio devices: `python3 -c "import sounddevice; print(sounddevice.query_devices())"`
- Update `AUDIO_DEVICE_NAME` in config.py if needed

### DMX Not Working
- Ensure OLA daemon is running: `systemctl status olad`
- Check OLA web interface: http://localhost:9090
- Verify DMX dongle is patched to Universe 1
- Test with OLA console: `ola_dmxconsole`

### GUI Doesn't Appear on Boot
- Verify auto-login is enabled in raspi-config
- Check service logs: `journalctl -u audio_dmx.service`
- Ensure DISPLAY environment variable is set correctly

## Project Structure

```
audio_reactive_lighting/
├── main.py          # Main orchestration script
├── audio.py         # Audio capture and beat detection
├── lighting.py      # DMX control and lighting patterns
├── ui.py            # Tkinter GUI
├── config.py        # Configuration and settings
├── setup.sh         # Installation script
├── audio_dmx.service # Systemd service file
└── README.md        # This file
```

## Performance Notes

- Optimized for Raspberry Pi 3B (1.2 GHz quad-core)
- Audio processing at ~11.6ms latency (512 samples @ 44.1kHz)
- DMX output at 30 FPS
- GUI updates at 5 FPS
- Typical CPU usage: 15-25%

## License

This project is designed for educational and personal use.

## Support

For issues or questions about configuration, check the inline documentation in each module or refer to the technical specification document.