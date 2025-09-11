"""
Base DMX controller class with shared functionality for Simple and Advanced modes.
"""

import array
import threading
import time
from ola.ClientWrapper import ClientWrapper
import config


class BaseDmxController:
    """Base class for DMX lighting control."""
    
    def __init__(self, audio_analyzer, beat_queue, stop_event):
        """
        Initialize the base DMX controller.
        
        Args:
            audio_analyzer: Reference to audio analyzer for state access
            beat_queue: Queue for beat events from audio module
            stop_event: Threading event to signal shutdown
        """
        self.audio_analyzer = audio_analyzer
        self.beat_queue = beat_queue
        self.stop_event = stop_event
        
        # Threading
        self.thread = None
        self.control_lock = threading.RLock()
        
        # OLA client
        self.ola_client = None
        self.wrapper = None
        
        # DMX state
        self.dmx_data = array.array('B', [0] * config.DMX_CHANNELS)
        self.active_lights = config.DEFAULT_LIGHT_COUNT
        
        # Beat tracking
        self.last_beat_time = 0
        self.beat_occurred = False
        
        # DMX frame update interval (milliseconds)
        self.update_interval = int(1000 / config.UPDATE_FPS)
        
    def start(self):
        """Start the DMX control thread."""
        self.thread = threading.Thread(target=self._dmx_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Stop the DMX control thread."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)
            
    def set_light_count(self, count):
        """Set the number of active lights."""
        with self.control_lock:
            self.active_lights = max(1, min(count, config.MAX_LIGHTS))
            
    def _setup_ola(self):
        """Initialize OLA client connection."""
        try:
            self.wrapper = ClientWrapper()
            self.ola_client = self.wrapper.Client()
            return True
        except Exception as e:
            print(f"Failed to connect to OLA: {e}")
            return False
            
    def _dmx_loop(self):
        """Main DMX control loop running in separate thread."""
        if not self._setup_ola():
            print("DMX control disabled - OLA not available")
            return
            
        print(f"DMX controller started on universe {config.DMX_UNIVERSE}")
        last_update = time.time()
        
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                # Check for beats
                self._process_beats()
                
                # Compute frame at target FPS
                if (current_time - last_update) * 1000 >= self.update_interval:
                    dmx_frame = self._compute_dmx_frame()
                    self._send_dmx(dmx_frame)
                    last_update = current_time
                    
                # Small sleep to prevent CPU spinning
                time.sleep(0.001)
                
            except Exception as e:
                print(f"DMX loop error: {e}")
                time.sleep(0.1)
                
        # Send blackout on exit
        self._send_dmx(array.array('B', [0] * config.DMX_CHANNELS))
        print("DMX controller stopped")
        
    def _process_beats(self):
        """Process beat events from queue."""
        self.beat_occurred = False
        while not self.beat_queue.empty():
            try:
                beat_data = self.beat_queue.get_nowait()
                self.beat_occurred = True
                self.last_beat_time = time.time()
            except:
                break
                
    def _compute_dmx_frame(self):
        """Compute the DMX channel values for current frame. Override in subclass."""
        return array.array('B', [0] * config.DMX_CHANNELS)
        
    def _send_dmx(self, data):
        """Send DMX data to OLA."""
        if self.ola_client:
            self.ola_client.SendDmx(config.DMX_UNIVERSE, data, self._dmx_sent)
            self.wrapper.Run()
            
    def _dmx_sent(self, status):
        """Callback for DMX send completion."""
        if not status.Succeeded():
            print(f"DMX send failed: {status}")
            
    def _set_light_color(self, data, light_index, r, g, b, brightness=1.0):
        """Helper to set a light's color in the DMX data array."""
        if light_index >= self.active_lights:
            return
            
        fixture = config.LIGHT_FIXTURES[light_index]
        base_channel = fixture['start_channel'] - 1
        channels = fixture['channels']
        
        # Apply brightness
        r = int(r * brightness)
        g = int(g * brightness)
        b = int(b * brightness)
        
        # Set DMX values
        if 'dimmer' in channels:
            data[base_channel + channels['dimmer']] = int(brightness * 255)
            
        if 'red' in channels:
            data[base_channel + channels['red']] = min(255, r)
        if 'green' in channels:
            data[base_channel + channels['green']] = min(255, g)
        if 'blue' in channels:
            data[base_channel + channels['blue']] = min(255, b)
            
        # Set mode to manual control (0-9 range, using 0)
        if 'mode' in channels:
            data[base_channel + channels['mode']] = 0
            
        # Set speed to 0 (we control timing)
        if 'speed' in channels:
            data[base_channel + channels['speed']] = 0