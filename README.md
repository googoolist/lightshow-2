# Audio-Reactive DMX Lighting System

A real-time audio-reactive lighting control system for DMX PAR lights, designed for Raspberry Pi. Creates smooth, dynamic lighting effects synchronized to music with an intuitive touchscreen interface.

## Features

### 🎵 Audio Processing
- Real-time beat detection and BPM tracking
- Dynamic intensity analysis  
- Automatic silence detection
- USB audio input support

### 💡 Lighting Effects
- **Smooth color transitions** with adjustable fade speeds
- **Beat-synchronized** brightness and color changes
- **5 Pattern Modes**:
  - **Sync**: All lights display synchronized colors
  - **Wave**: Colors flow across lights in a wave pattern
  - **Center**: Center lights lead, outer lights follow
  - **Alternate**: Lights alternate in groups
  - **Mirror**: Symmetric mirroring from center outward
- **Dynamic light count**: Support for 1-8 DMX lights

### 🎛️ Control Interface (320x480 touchscreen optimized)
- **Speed Slider**: Control transition speed (Slow ↔ Fast)
- **Rainbow Slider**: Adjust color diversity (Single ↔ Full spectrum)
- **Brightness Slider**: Master brightness control (10% ↔ 120%)
- **Strobe Slider**: Beat-triggered strobe intensity (Off ↔ Max)
- **Pattern Selector**: Choose from 5 movement patterns
- **Light Count Control**: Dynamically adjust number of active lights (1-8)
- **Real-time Status**: BPM and audio level display

## System Requirements

### Hardware
- Raspberry Pi 3B or newer
- USB audio input device
- USB DMX adapter (FTDI-based)
- DMX PAR lights (up to 8 supported)
- Optional: 320x480 touchscreen display

### Software
- Raspberry Pi OS with Desktop
- Python 3.7+
- OLA (Open Lighting Architecture)
- Required Python packages (see Installation)

## Installation

### Quick Install
```bash
cd ~
git clone [your-repo-url] lightshow-2
cd lightshow-2/app
bash install.sh
```

The installer handles:
- System dependencies
- Python virtual environment
- OLA configuration for DMX
- Auto-start setup
- System optimizations

### Configure DMX
1. Open browser: `http://localhost:9090`
2. Add your USB DMX device
3. Patch it to Universe 1
4. Reboot to start automatically

## Configuration

Edit `config.py` to customize:

### DMX Settings
```python
DMX_UNIVERSE = 1                   # OLA universe
DMX_CHANNELS = 64                  # Total channels (8 lights × 8 channels)
DEFAULT_LIGHT_COUNT = 3            # Starting number of lights
MAX_LIGHTS = 8                     # Maximum supported
```

### Light Channel Mapping
Each PAR light uses 8 DMX channels:
- Channel 1: Dimmer
- Channel 2: Red
- Channel 3: Green  
- Channel 4: Blue
- Channel 5: White (if available)
- Channel 6: Strobe (if available)
- Channel 7: Mode/Macro
- Channel 8: (Reserved)

Default assignments:
- PAR 1: DMX 1-8
- PAR 2: DMX 9-16
- PAR 3: DMX 17-24
- PAR 4: DMX 25-32
- (up to PAR 8: DMX 57-64)

### Audio Settings
```python
SAMPLE_RATE = 44100                # Audio sampling rate
BUFFER_SIZE = 512                  # Audio buffer size
SILENCE_THRESHOLD = 0.01           # RMS threshold for silence
MIN_BPM = 60                       # Minimum BPM detection
MAX_BPM = 180                      # Maximum BPM detection
```

### Default Effect Settings
```python
LIGHTING_SETTINGS = {
    "brightness_base": 0.6,        # Base brightness (60%)
    "intensity_smoothing": 0.95,   # Audio smoothing factor
    "beat_flash_duration": 0.5,    # Beat flash length
    "beat_response": 0.2,          # Beat sensitivity
}
```

## Usage

### Manual Start
```bash
cd ~/lightshow-2/app

# Option 1: Using autostart script
./autostart.sh

# Option 2: Direct execution
./venv/bin/python main.py

# Option 3: Headless mode (no GUI)
./venv/bin/python main.py --headless
```

### Controls

#### Sliders (Left Column)
- **Speed**: Transition speed control
  - Left (Slow): Smooth, gradual transitions
  - Right (Fast): Quick, snappy changes
  - Affects: Color fades, beat response, pattern speed

- **Rainbow**: Color diversity control
  - Left (Single): All lights same color
  - Right (Full): Maximum color variety
  - Affects: Color selection, change frequency

- **Brightness**: Master brightness
  - Left (Dim): 10% brightness for ambiance
  - Right (Bright): 120% boosted brightness
  - Affects: Overall light intensity

#### Controls (Right Column)
- **Strobe**: Beat-triggered strobe
  - Left (Off): No strobe effect
  - Right (Max): Maximum strobe on beats
  - Only triggers on strong beats

- **Pattern**: Movement patterns
  - Sync: Synchronized colors
  - Wave: Flowing wave effect
  - Center: Center-out propagation
  - Alternate: Alternating groups
  - Mirror: Symmetric patterns

- **Lights [−] 3 [+]**: Active light count
  - Range: 1-8 lights
  - Dynamically adjusts patterns
  - Click [+] to add, [−] to remove

#### Keyboard Shortcuts
- **ESC** or **Q**: Exit application
- **Alt+Tab**: Switch applications (when not fullscreen)

### Fullscreen Mode
To enable fullscreen kiosk mode, edit `config.py`:
```python
FULLSCREEN = True
```

## Slider Ranges & Effects

### Speed Slider (controls smoothness internally)
- **0% (Left)**: Ultra-fast transitions, instant color changes
- **50% (Center)**: Balanced, moderate speed
- **100% (Right)**: Very slow, meditative transitions

The Speed slider has expanded range control:
- Below 50%: Progressively faster (100x range)
- Above 50%: Progressively slower (40x range)

### Rainbow Slider  
- **0-20%**: Single color mode, slow changes
- **20-50%**: Moderate diversity, occasional changes
- **50-80%**: High diversity, frequent changes
- **80-100%**: Full rainbow, rapid color cycling

### Brightness Slider
- **0%**: 10% brightness (very dim mood lighting)
- **50%**: 100% brightness (normal)
- **100%**: 120% brightness (boosted party mode)

## Troubleshooting

### Check Logs
```bash
# Auto-start log
cat ~/lightshow-2/app/autostart.log

# Application log
cat ~/lightshow-2/app/startup.log
```

### Check Services
```bash
# OLA status
systemctl status olad

# Test DMX output
ola_dmxconsole -u 1
```

### Common Issues

**No audio detected:**
- Check USB audio device: `arecord -l`
- Verify audio input levels
- Adjust `SILENCE_THRESHOLD` in config.py

**Lights not responding:**
- Verify OLA configuration at http://localhost:9090
- Check DMX adapter is recognized: `ls /dev/ttyUSB*`
- Ensure FTDI plugin is enabled in OLA
- Test with: `ola_dmxconsole -u 1`

**GUI hangs on startup:**
- Already fixed in latest version
- Pull latest changes if experiencing issues

**Performance issues:**
- Reduce `UPDATE_FPS` in config.py (default: 30)
- Increase `GUI_UPDATE_INTERVAL` (default: 200ms)
- Reduce number of active lights

## Advanced Features

### Custom Color Palettes
Edit `SMOOTH_COLOR_PALETTE` in config.py to define custom colors:
```python
SMOOTH_COLOR_PALETTE = [
    (255, 0, 0),      # Red
    (255, 128, 0),    # Orange
    (255, 255, 0),    # Yellow
    # Add your colors (R, G, B)
]
```

### Pattern Customization
Patterns automatically adapt to the number of active lights:
- 1 light: All patterns work as single light effects
- 2 lights: Simple alternation and mirroring
- 3+ lights: Full pattern complexity
- 4+ lights: Enhanced center patterns (dual center for even counts)

### Beat Detection Tuning
Adjust in config.py:
```python
BEAT_CONFIDENCE_THRESH = 0.2  # Lower = more sensitive
WIN_SIZE = 1024               # FFT window size
HOP_SIZE = 512                # Analysis hop size
```

## Development

### Project Structure
```
lightshow-2/
├── README.md         # This documentation
├── INSTALL.md        # Installation guide
└── app/              # Application folder
    ├── main.py       # Main orchestration
    ├── audio.py      # Audio processing & beat detection
    ├── lighting.py   # DMX control & patterns
    ├── ui.py         # Tkinter GUI
    ├── config.py     # Configuration & settings
    ├── install.sh    # Installation script
    ├── uninstall.sh  # Uninstall script
    └── autostart.sh  # Auto-start script
```

### Adding New Patterns
1. Add pattern name to UI combobox in `ui.py`
2. Implement pattern logic in `lighting.py` `_apply_pattern()` method
3. Pattern will automatically adapt to active light count

### Extending Light Support
The system supports up to 8 lights by default. To add more:
1. Add fixture definitions in `config.py` `LIGHT_FIXTURES`
2. Update `MAX_LIGHTS` constant
3. Increase `DMX_CHANNELS` accordingly

## Uninstall

To remove the application:
```bash
cd ~/lightshow-2/app
bash uninstall.sh
```

This removes:
- Auto-start configuration
- Python virtual environment
- System service files

System packages (Python, OLA) are preserved.

## License

This project is designed for educational and personal use.

## Acknowledgments

Built with:
- [OLA (Open Lighting Architecture)](https://www.openlighting.org/)
- [aubio](https://aubio.org/) for beat detection
- [NumPy](https://numpy.org/) for signal processing
- [sounddevice](https://python-sounddevice.readthedocs.io/) for audio capture

## Support

For issues or questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review logs in the installation directory
- Ensure all hardware connections are secure
- Verify DMX termination if using long cable runs