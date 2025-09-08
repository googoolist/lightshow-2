"""
DMX lighting control module for managing PAR lights via OLA.
"""

import array
import threading
import time
from ola.ClientWrapper import ClientWrapper
import config


class DmxController:
    def __init__(self, audio_analyzer, beat_queue, stop_event):
        """
        Initialize the DMX controller.
        
        Args:
            audio_analyzer: Reference to audio analyzer for state access
            beat_queue: Queue for receiving beat events
            stop_event: Threading event to signal shutdown
        """
        self.audio_analyzer = audio_analyzer
        self.beat_queue = beat_queue
        self.stop_event = stop_event
        
        # OLA client setup
        self.wrapper = None
        self.client = None
        
        # Lighting state
        self.current_color_index = 0
        self.lights_on = [True, True, True]  # Track on/off state for each PAR
        self.beat_flash_time = [0, 0, 0]  # Track flash timing for each PAR
        self.last_beat_time = 0
        
        # DMX frame update interval (milliseconds)
        self.update_interval = int(1000 / config.UPDATE_FPS)
        
    def start(self):
        """Start the DMX control thread."""
        self.thread = threading.Thread(target=self._dmx_loop, daemon=True)
        self.thread.start()
    
    def _setup_ola(self):
        """Initialize OLA client connection."""
        try:
            self.wrapper = ClientWrapper()
            self.client = self.wrapper.Client()
            return True
        except Exception as e:
            print(f"Failed to connect to OLA: {e}")
            return False
    
    def _dmx_loop(self):
        """Main DMX control loop running in separate thread."""
        if not self._setup_ola():
            print("DMX controller failed to initialize")
            return
        
        # Schedule first DMX frame
        self.wrapper.AddEvent(self.update_interval, self._send_dmx_frame)
        
        # Run OLA event loop (blocks until Stop() is called)
        self.wrapper.Run()
    
    def _send_dmx_frame(self):
        """Send a DMX frame and schedule the next one."""
        if self.stop_event.is_set():
            self.wrapper.Stop()
            return
        
        # Compute and send frame
        frame = self._compute_dmx_frame()
        self.client.SendDmx(config.DMX_UNIVERSE, frame, self._dmx_callback)
        
        # Schedule next frame
        self.wrapper.AddEvent(self.update_interval, self._send_dmx_frame)
    
    def _dmx_callback(self, status):
        """Callback after DMX send."""
        if not status.Succeeded():
            print(f"DMX send failed: {status}")
    
    def _compute_dmx_frame(self):
        """Compute the DMX channel values for current frame."""
        # Initialize DMX data array
        data = array.array('B', [0] * config.DMX_CHANNELS)
        
        # Get current audio state
        audio_state = self.audio_analyzer.get_state()
        intensity = audio_state['intensity']
        audio_active = audio_state['audio_active']
        
        # Process any pending beat events
        beat_occurred = False
        while not self.beat_queue.empty():
            try:
                beat_event = self.beat_queue.get_nowait()
                beat_occurred = True
                self.last_beat_time = time.time()
            except:
                break
        
        # Handle beat events
        if beat_occurred:
            self._handle_beat_event()
        
        # If no audio, turn lights off
        if not audio_active:
            return data  # All zeros = lights off
        
        # Get current color from preset
        color = config.COLOR_PRESETS[self.current_color_index]
        
        # Process each PAR light
        for i, fixture in enumerate(config.LIGHT_FIXTURES):
            base_channel = fixture['start_channel'] - 1  # Convert to 0-indexed
            channels = fixture['channels']
            
            # Check if this light should flash (beat flash effect)
            flash_active = (time.time() - self.beat_flash_time[i]) < config.BEAT_FLASH_DURATION
            
            # Calculate brightness based on intensity and flash
            if flash_active:
                brightness = 255  # Full brightness during flash
            else:
                brightness = int(intensity * 255 * config.BRIGHTNESS_BASE)
            
            # Determine if light should be on (for alternating mode)
            if config.ALTERNATING_MODE:
                # Alternate lights on beats
                light_active = self.lights_on[i]
            else:
                light_active = True
            
            if light_active:
                # Set dimmer channel
                if 'dimmer' in channels:
                    data[base_channel + channels['dimmer']] = brightness
                
                # Set RGB colors (scaled by brightness if no dimmer)
                if 'dimmer' not in channels:
                    # Scale colors directly if no dimmer channel
                    scale = brightness / 255.0
                else:
                    scale = 1.0  # Dimmer handles brightness
                
                if 'red' in channels:
                    data[base_channel + channels['red']] = int(color[0] * scale)
                if 'green' in channels:
                    data[base_channel + channels['green']] = int(color[1] * scale)
                if 'blue' in channels:
                    data[base_channel + channels['blue']] = int(color[2] * scale)
                
                # Set white channel if available (mix of RGB)
                if 'white' in channels:
                    white_value = int(min(color) * scale * 0.5)  # Use minimum RGB as white
                    data[base_channel + channels['white']] = white_value
                
                # Strobe effect on beat (if channel available)
                if 'strobe' in channels and flash_active:
                    data[base_channel + channels['strobe']] = 255  # Fast strobe during beat
                else:
                    if 'strobe' in channels:
                        data[base_channel + channels['strobe']] = 0  # No strobe
            else:
                # Light is off
                if 'dimmer' in channels:
                    data[base_channel + channels['dimmer']] = 0
        
        return data
    
    def _handle_beat_event(self):
        """Process a beat event - update colors and light states."""
        # Cycle colors if enabled
        if config.COLOR_CYCLE_ON_BEAT:
            self.current_color_index = (self.current_color_index + 1) % len(config.COLOR_PRESETS)
        
        # Handle alternating mode
        if config.ALTERNATING_MODE:
            # Create different patterns for 3 lights
            beat_count = int(time.time() * 2) % 3  # Simple pattern counter
            
            # Pattern 1: Rotate which light is on
            if beat_count == 0:
                self.lights_on = [True, False, False]
            elif beat_count == 1:
                self.lights_on = [False, True, False]
            else:
                self.lights_on = [False, False, True]
            
            # Set flash time for active lights
            for i in range(3):
                if self.lights_on[i]:
                    self.beat_flash_time[i] = time.time()
        else:
            # All lights flash together
            for i in range(3):
                self.beat_flash_time[i] = time.time()
    
    def stop(self):
        """Stop the DMX control thread."""
        self.stop_event.set()
        
        # Send all zeros to turn lights off before stopping
        if self.client:
            try:
                off_frame = array.array('B', [0] * config.DMX_CHANNELS)
                self.client.SendDmx(config.DMX_UNIVERSE, off_frame, lambda s: None)
            except:
                pass
        
        # Stop OLA wrapper if running
        if self.wrapper:
            try:
                self.wrapper.Stop()
            except:
                pass
        
        # Wait for thread to finish
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)