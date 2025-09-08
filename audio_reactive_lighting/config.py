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

# Lighting behavior settings
BRIGHTNESS_BASE = 1.0              # Base brightness scalar (0.0-1.0)
INTENSITY_SMOOTHING = 0.7          # Smoothing factor for intensity (0-1, higher = smoother)
BEAT_FLASH_DURATION = 0.1          # Duration of beat flash in seconds
ALTERNATING_MODE = True            # If True, alternate PAR lights on beats
COLOR_CYCLE_ON_BEAT = True         # If True, cycle colors on each beat

# GUI settings
GUI_UPDATE_INTERVAL = 200          # GUI refresh interval in milliseconds
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 300
FULLSCREEN = False                 # Set to True for kiosk mode