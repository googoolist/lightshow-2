# Audio-Reactive DMX Lighting System

A real-time audio-reactive lighting control system for DMX PAR lights, designed for Raspberry Pi. Creates smooth, dynamic lighting effects synchronized to music with an intuitive touchscreen interface.

## Features

### 🎵 Audio Processing
- Real-time beat detection and BPM tracking
- Dynamic intensity analysis  
- Automatic silence detection
- USB audio input support

### 💡 Lighting System
- **Dual Mode Operation**: Simple mode for easy presets, Advanced mode for full control
- **Beat-synchronized** effects with adjustable BPM divisions
- **Frequency-reactive** programs that respond to bass, mids, and highs
- **Volume-reactive** effects for dynamic intensity
- **15 Simple Mode Programs** with minimal controls
- **Advanced Mode** with extensive customization options
- **Dynamic light count**: Support for 1-8 DMX lights

### 🎛️ Control Interface (320x480 touchscreen optimized)
- **Mode Selector**: Switch between Simple and Advanced modes
- **Simple Mode**: Program selector with BPM sync, dimming, and cool colors toggle
- **Advanced Mode**: Full control with multiple tabs for effects and settings
- **Real-time Status**: BPM, audio level, and frequency spectrum display
- **Dynamic light count**: Adjust number of active lights (1-8)

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

### Mode Selection

The system starts in **Simple Mode** by default. Use the radio buttons at the top to switch between modes.

## Simple Mode Controls

### Program Selector
Choose from 15 preset programs:

#### Movement Programs
- **Bounce (Same Color)**: Wave bounces left-right with smooth fade, same color
- **Bounce (Different Colors)**: Wave bounces with each light keeping its own color
- **Bounce (Discrete)**: Single light bounces without fade (strobing effect)
- **Swell (Same Color)**: All lights breathe together with the same color
- **Swell (Different Colors)**: All lights breathe together, each with different color

#### Party Programs
- **Disco**: Random fading lights with varied colors and speeds
- **Psych**: Psychedelic flowing waves with color morphing
- **Strobe**: Sharp on/off flashing synchronized to beats
- **Alternating**: Even/odd lights toggle in patterns

#### Audio-Reactive Programs
- **Pulse**: All lights pulse brightness with music volume (volume-reactive)
- **Spectrum**: Display frequency bands - bass (left), mids (center), highs (right)
- **VU Meter**: Horizontal volume meter with green→yellow→red gradient
- **Chase**: Continuous light traveling left to right with tail
- **Center Burst**: Explosion effect from center outward on beats
- **Ripple**: Multiple overlapping waves flowing across lights

### Simple Mode Controls

#### BPM Sync Slider
Controls how often effects trigger based on detected BPM:
- **1x**: Every beat (fastest)
- **2x**: Every 2nd beat (half speed)
- **4x**: Every 4th beat (quarter speed)
- **8x**: Every 8th beat
- **16x**: Every 16th beat (slowest)

Example: At 120 BPM with 4x setting, effects trigger every 2 seconds (30 times per minute)

#### Dimming Slider
- **0%**: Lights completely off
- **50%**: Half brightness
- **100%**: Full brightness
- Controls overall intensity for all programs

#### Cool Colors Checkbox
- **Unchecked**: Full color palette (reds, oranges, yellows, greens, blues, purples)
- **Checked**: Cool colors only (blues, greens, teals, purples - no reds/oranges)

## Advanced Mode Controls

Advanced mode provides full control through three tabs:

### Main Tab

#### Left Column
- **Speed**: Transition speed (0% = very fast, 100% = very slow)
  - Controls how quickly colors fade and change
  - Affects smoothness of all effects
  
- **Rainbow**: Color diversity (0% = single color, 100% = full spectrum)
  - At 0%: All lights same color
  - At 50%: Moderate variety
  - At 100%: Maximum color diversity
  
- **Brightness**: Master brightness (0% = 10% dim, 100% = 120% boosted)

- **BPM Sync**: Beat division dropdown
  - Same as Simple mode (Every beat, Every 2 beats, etc.)

- **Lights Counter**: [−] number [+]
  - Adjust active light count (1-8)

#### Right Column  
- **Strobe**: Beat-triggered strobe intensity (0% = off, 100% = maximum)
  
- **Beat Sensitivity**: How strongly lights react to beats
  - 0% = Subtle beat response
  - 100% = Intense beat reaction
  
- **Pattern**: Movement pattern selector
  - Sync: All lights synchronized
  - Wave: Flowing wave across lights
  - Center: Center-out propagation
  - Alternate: Alternating groups
  - Mirror: Symmetric from center
  - Swell: Breathing effect

### Effects Tab

#### Sliders
- **Chaos**: Randomness level (0% = predictable, 100% = wild variations)
- **Echo**: Light trail/echo length (0% = off, 100% = long trails)

#### Theme Selector
Pre-defined color palettes:
- **Default**: Full spectrum colors
- **Sunset**: Warm reds, oranges, yellows
- **Ocean**: Blues, teals, aquas
- **Fire**: Reds, oranges, whites
- **Forest**: Greens, browns, yellows
- **Galaxy**: Purples, blues, pinks
- **Mono**: Single color variations
- **Warm**: Warm color tones
- **Cool**: Cool color tones

#### Effect Mode
Special animation effects:
- **None**: No additional effect
- **Breathe**: Gentle breathing animation
- **Sparkle**: Random sparkle overlay
- **Chase**: Sequential light chase
- **Pulse**: Pulsing intensity
- **Sweep**: Sweeping motion
- **Firefly**: Random firefly-like flashes

#### Mode Toggles (Checkboxes)
- **Mood Match**: Automatically adjust colors based on music mood
- **Frequency**: Colors respond to frequency content (bass=red, high=blue)
- **Ambient**: Gentle, slow changes for background ambiance
- **Auto Genre**: Detect music genre and adjust effects accordingly
- **Spectrum**: Display live frequency spectrum

### Status Tab
Displays real-time information:
- **Frequency Analysis**: Live bass, mid, and high frequency levels with progress bars
- **Genre Detection**: Currently detected music genre
- **Event Detection**: Shows "Building..." during buildups, "DROP!" on drops
- **DMX Info**: Universe number, channel count, and FPS

#### Keyboard Shortcuts
- **ESC** or **Q**: Exit application
- **Alt+Tab**: Switch applications (when not fullscreen)

### Fullscreen Mode
To enable fullscreen kiosk mode, edit `config.py`:
```python
FULLSCREEN = True
```

## Technical Details

### Beat Division Mathematics
When using BPM Sync controls:
- **Every beat (1x)**: Triggers at detected BPM rate
- **Every 2 beats (2x)**: Triggers at BPM ÷ 2 
- **Every 4 beats (4x)**: Triggers at BPM ÷ 4
- **Every 8 beats (8x)**: Triggers at BPM ÷ 8
- **Every 16 beats (16x)**: Triggers at BPM ÷ 16

Example at 128 BPM:
- 1x = 128 triggers/minute (every 0.47 seconds)
- 2x = 64 triggers/minute (every 0.94 seconds)
- 4x = 32 triggers/minute (every 1.88 seconds)
- 8x = 16 triggers/minute (every 3.75 seconds)
- 16x = 8 triggers/minute (every 7.5 seconds)

### Frequency Band Analysis
The Spectrum program and frequency-reactive modes analyze audio in three bands:
- **Bass**: 20-250 Hz (kick drums, bass lines)
- **Mids**: 250-2000 Hz (vocals, instruments)
- **Highs**: 2000-20000 Hz (cymbals, harmonics)

### Volume Reactivity
Programs like Pulse and VU Meter respond to RMS (Root Mean Square) volume:
- Calculated over 512-sample windows
- Smoothed with 0.95 factor to prevent jitter
- Normalized 0.0 to 1.0 scale
- Minimum threshold of 0.01 to detect silence

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
├── README.md           # This documentation
├── INSTALL.md          # Installation guide
└── app/                # Application folder
    ├── main.py         # Main orchestration
    ├── audio.py        # Audio processing & beat detection
    ├── lighting_base.py    # Base DMX controller class
    ├── lighting_simple.py  # Simple mode with 15 programs
    ├── lighting_advanced.py # Advanced mode controller
    ├── ui.py           # Main UI with mode switching
    ├── ui_simple.py    # Simple mode interface
    ├── ui_advanced.py  # Advanced mode interface
    ├── config.py       # Configuration & settings
    ├── install.sh      # Installation script
    ├── uninstall.sh    # Uninstall script
    └── autostart.sh    # Auto-start script
```

### Adding New Programs
#### For Simple Mode:
1. Add program name to `PROGRAMS` list in `lighting_simple.py`
2. Add to UI combobox in `ui_simple.py`
3. Implement `_program_name()` method in `lighting_simple.py`
4. Initialize any state variables in `__init__` and `_init_light_states()`

#### For Advanced Mode:
1. Add pattern name to pattern combobox in `ui_advanced.py`
2. Implement pattern logic in `lighting_advanced.py` `_apply_pattern()` method
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