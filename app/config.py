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
DMX_CHANNELS = 64                  # Total channels to send (8 PARs * 8 channels max)
UPDATE_FPS = 30                    # DMX update frequency
DEFAULT_LIGHT_COUNT = 3            # Default number of active lights
MAX_LIGHTS = 8                     # Maximum supported lights

# PAR light configuration - Up to 8 PAR lights with RGBW or similar channels
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
    },
    {
        "name": "PAR4",
        "start_channel": 25,
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
        "name": "PAR5",
        "start_channel": 33,
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
        "name": "PAR6",
        "start_channel": 41,
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
        "name": "PAR7",
        "start_channel": 49,
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
        "name": "PAR8",
        "start_channel": 57,
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

# Default lighting settings (Ultra smooth relaxing waves)
LIGHTING_SETTINGS = {
    "brightness_base": 0.6,        # Softer base brightness for ambiance
    "intensity_smoothing": 0.95,   # Very smooth intensity changes
    "beat_flash_duration": 0.5,    # Longer, gentler beat flashes
    "beat_response": 0.2,          # Very subtle beat response
}

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

# Warm color palette (reds, oranges, yellows)
WARM_COLOR_PALETTE = [
    (255, 0, 0),      # Red
    (255, 32, 0),     # Red-orange
    (255, 64, 0),     # Orange-red
    (255, 96, 0),     # Deep orange
    (255, 128, 0),    # Orange
    (255, 160, 0),    # Light orange
    (255, 192, 0),    # Gold
    (255, 224, 0),    # Golden yellow
    (255, 255, 0),    # Yellow
    (255, 255, 64),   # Light yellow
    (255, 192, 128),  # Peach
    (255, 128, 64),   # Coral
]

# Cool color palette (blues, purples, cyans)
COOL_COLOR_PALETTE = [
    (0, 0, 255),      # Blue
    (0, 64, 255),     # Light blue
    (0, 128, 255),    # Sky blue
    (0, 192, 255),    # Bright sky
    (0, 255, 255),    # Cyan
    (0, 255, 192),    # Aqua
    (0, 255, 128),    # Teal
    (64, 128, 255),   # Periwinkle
    (128, 0, 255),    # Purple
    (192, 0, 255),    # Violet
    (255, 0, 255),    # Magenta
    (255, 0, 192),    # Pink-purple
]

# GUI settings
GUI_UPDATE_INTERVAL = 200          # GUI refresh interval in milliseconds
WINDOW_WIDTH = 480                 # Width for small touchscreen
WINDOW_HEIGHT = 320                # Height for small touchscreen (landscape orientation)
FULLSCREEN = True                  # Set to True for fullscreen kiosk mode (ESC or Q to exit)