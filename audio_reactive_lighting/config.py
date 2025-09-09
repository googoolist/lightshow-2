"""
Configuration and constants for the audio-reactive DMX lighting system.
"""

# Audio settings
AUDIO_DEVICE_NAME = None           # None for default USB audio input
SAMPLE_RATE = 44100                # Sampling rate in Hz
BUFFER_SIZE = 512                  # Block size for audio processing (hop size)
SILENCE_THRESHOLD = 0.01           # RMS threshold to consider as silence
SILENCE_FRAME_COUNT = 44           # Number of silent frames (~0.5s) before marking as paused

# Beat detection settings
WIN_SIZE = 1024                    # Window size for aubio tempo
HOP_SIZE = 512                     # Hop size for aubio (match BUFFER_SIZE)
MIN_BPM = 60                       # Minimum expected BPM
MAX_BPM = 180                      # Maximum expected BPM
BEAT_CONFIDENCE_THRESH = 0.2       # Confidence threshold for beat detection

# DMX/Lighting settings
DMX_UNIVERSE = 1                   # OLA universe to send to
DMX_CHANNELS = 24                  # Total channels to send (3 PARs * 8 channels max)
UPDATE_FPS = 30                    # DMX update frequency

# PAR light configuration - 3 PAR lights with RGBW or similar channels
# Adjust channel mappings based on your specific PAR light models
LIGHT_FIXTURES = [
    {
        "name": "PAR1",
        "start_channel": 1,
        "channels": {
            "dimmer": 0,    # Channel offset from start_channel
            "red": 1,
            "green": 2,
            "blue": 3,
            "white": 4,     # If your PAR has white channel
            "strobe": 5,    # If your PAR has strobe
            "mode": 6,      # Mode/macro channel if available
        }
    },
    {
        "name": "PAR2", 
        "start_channel": 9,
        "channels": {
            "dimmer": 0,
            "red": 1,
            "green": 2,
            "blue": 3,
            "white": 4,
            "strobe": 5,
            "mode": 6,
        }
    },
    {
        "name": "PAR3",
        "start_channel": 17,
        "channels": {
            "dimmer": 0,
            "red": 1,
            "green": 2,
            "blue": 3,
            "white": 4,
            "strobe": 5,
            "mode": 6,
        }
    }
]

# Color presets for beat cycling
COLOR_PRESETS = [
    (255, 0, 0),      # Red
    (0, 255, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 255, 0),    # Yellow
    (255, 0, 255),    # Magenta
    (0, 255, 255),    # Cyan
    (255, 128, 0),    # Orange
    (128, 0, 255),    # Purple
]

# Lighting modes
LIGHTING_MODES = {
    "smooth": {
        "name": "Smooth & Mellow",
        "description": "Gentle fading transitions with rich colors",
        "brightness_base": 0.7,
        "intensity_smoothing": 0.9,
        "beat_flash_duration": 0.3,
        "alternating": False,
        "color_cycle_on_beat": False,
        "fade_speed": 0.02,  # Slow fade between colors
        "beat_response": 0.3,  # Subtle beat response
    },
    "rapid": {
        "name": "Rapid Beat Sync",
        "description": "Fast changes synchronized to beat",
        "brightness_base": 1.0,
        "intensity_smoothing": 0.3,
        "beat_flash_duration": 0.05,
        "alternating": True,
        "color_cycle_on_beat": True,
        "fade_speed": 0,  # No fading, instant changes
        "beat_response": 1.0,  # Strong beat response
    },
    "classic": {
        "name": "Classic",
        "description": "Original configuration",
        "brightness_base": 1.0,
        "intensity_smoothing": 0.7,
        "beat_flash_duration": 0.1,
        "alternating": True,
        "color_cycle_on_beat": True,
        "fade_speed": 0,
        "beat_response": 0.7,
    }
}

# Default mode
DEFAULT_LIGHTING_MODE = "classic"

# Extended color palette for smooth mode
SMOOTH_COLOR_PALETTE = [
    (255, 0, 0),      # Red
    (255, 64, 0),     # Orange-red
    (255, 128, 0),    # Orange
    (255, 192, 0),    # Gold
    (255, 255, 0),    # Yellow
    (192, 255, 0),    # Yellow-green
    (0, 255, 0),      # Green
    (0, 255, 128),    # Teal
    (0, 255, 255),    # Cyan
    (0, 128, 255),    # Sky blue
    (0, 0, 255),      # Blue
    (128, 0, 255),    # Purple
    (255, 0, 255),    # Magenta
    (255, 0, 128),    # Pink
]

# GUI settings
GUI_UPDATE_INTERVAL = 200          # GUI refresh interval in milliseconds
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 400                # Increased to accommodate mode selector
FULLSCREEN = False                 # Set to True for kiosk mode