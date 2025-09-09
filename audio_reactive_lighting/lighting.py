"""
DMX lighting control module for managing PAR lights via OLA.
"""

import array
import threading
import time
import math
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
        
        # Lighting mode
        self.current_mode = config.DEFAULT_LIGHTING_MODE
        self.mode_settings = config.LIGHTING_MODES[self.current_mode]
        self.mode_lock = threading.Lock()
        
        # Lighting state
        self.current_color_index = 0
        self.lights_on = [True, True, True]  # Track on/off state for each PAR
        self.beat_flash_time = [0, 0, 0]  # Track flash timing for each PAR
        self.last_beat_time = 0
        
        # Smooth mode specific state
        self.target_colors = [(0, 0, 0)] * 3  # Target colors for each PAR
        self.current_colors = [(0, 0, 0)] * 3  # Current colors for smooth fading
        self.color_fade_progress = [0.0] * 3  # Fade progress for each PAR
        self.last_color_change = 0
        
        # DMX frame update interval (milliseconds)
        self.update_interval = int(1000 / config.UPDATE_FPS)
        
    def start(self):
        """Start the DMX control thread."""
        self.thread = threading.Thread(target=self._dmx_loop, daemon=True)
        self.thread.start()
    
    def set_mode(self, mode_name):
        """Change the lighting mode."""
        if mode_name in config.LIGHTING_MODES:
            with self.mode_lock:
                self.current_mode = mode_name
                self.mode_settings = config.LIGHTING_MODES[mode_name]
                print(f"Lighting mode changed to: {self.mode_settings['name']}")
                
                # Reset mode-specific state
                if mode_name == "smooth":
                    # Initialize smooth transitions
                    self.last_color_change = time.time()
                    for i in range(3):
                        self.target_colors[i] = config.SMOOTH_COLOR_PALETTE[i % len(config.SMOOTH_COLOR_PALETTE)]
    
    def get_current_mode(self):
        """Get the current lighting mode name."""
        with self.mode_lock:
            return self.current_mode
    
    def _setup_ola(self):
        """Initialize OLA client connection."""
        try:
            self.wrapper = ClientWrapper()
            self.client = self.wrapper.Client()
            print(f"OLA client connected successfully")
            print(f"Sending DMX to universe {config.DMX_UNIVERSE}")
            return True
        except Exception as e:
            print(f"Failed to connect to OLA: {e}")
            import traceback
            traceback.print_exc()
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
        
        # Debug: Show first few channels if any are non-zero
        non_zero = [i for i, v in enumerate(frame) if v > 0]
        if non_zero:
            preview = list(frame[:24])  # Show first 24 channels
            print(f"DMX Frame: {preview} (non-zero channels: {non_zero[:10]})")
        
        self.client.SendDmx(config.DMX_UNIVERSE, frame, self._dmx_callback)
        
        # Schedule next frame
        self.wrapper.AddEvent(self.update_interval, self._send_dmx_frame)
    
    def _dmx_callback(self, status):
        """Callback after DMX send."""
        if not status.Succeeded():
            print(f"DMX send failed: {status}")
            print(f"Error details: {status.message if hasattr(status, 'message') else 'Unknown error'}")
    
    def _compute_dmx_frame(self):
        """Compute the DMX channel values for current frame."""
        with self.mode_lock:
            mode = self.current_mode
            settings = self.mode_settings
        
        if mode == "smooth":
            return self._compute_smooth_frame()
        elif mode == "rapid":
            return self._compute_rapid_frame()
        else:  # classic
            return self._compute_classic_frame()
    
    def _compute_smooth_frame(self):
        """Compute DMX frame for smooth/mellow mode with fading transitions."""
        data = array.array('B', [0] * config.DMX_CHANNELS)
        settings = self.mode_settings
        
        # Get current audio state
        audio_state = self.audio_analyzer.get_state()
        intensity = audio_state['intensity']
        audio_active = audio_state['audio_active']
        
        if not audio_active:
            return data
        
        # Process beat events
        beat_occurred = False
        while not self.beat_queue.empty():
            try:
                self.beat_queue.get_nowait()
                beat_occurred = True
                self.last_beat_time = time.time()
            except:
                break
        
        # Smooth color transitions
        current_time = time.time()
        
        # Change target colors gradually (every 4-8 seconds or on strong beats)
        if current_time - self.last_color_change > 6.0 or (beat_occurred and intensity > 0.7):
            self.last_color_change = current_time
            # Rotate through extended color palette
            for i in range(3):
                current_idx = config.SMOOTH_COLOR_PALETTE.index(self.target_colors[i]) if self.target_colors[i] in config.SMOOTH_COLOR_PALETTE else 0
                next_idx = (current_idx + 1 + i) % len(config.SMOOTH_COLOR_PALETTE)
                self.target_colors[i] = config.SMOOTH_COLOR_PALETTE[next_idx]
                self.color_fade_progress[i] = 0.0
        
        # Update fade progress for each light
        for i in range(3):
            if self.color_fade_progress[i] < 1.0:
                self.color_fade_progress[i] = min(1.0, self.color_fade_progress[i] + settings['fade_speed'])
                
                # Interpolate between current and target colors
                r_current, g_current, b_current = self.current_colors[i]
                r_target, g_target, b_target = self.target_colors[i]
                
                progress = self.color_fade_progress[i]
                # Smooth ease-in-out interpolation
                smooth_progress = 0.5 - 0.5 * math.cos(progress * math.pi) if 'math' in dir() else progress
                
                self.current_colors[i] = (
                    int(r_current + (r_target - r_current) * smooth_progress),
                    int(g_current + (g_target - g_current) * smooth_progress),
                    int(b_current + (b_target - b_current) * smooth_progress)
                )
        
        # Apply colors to DMX channels
        for i, fixture in enumerate(config.LIGHT_FIXTURES):
            base_channel = fixture['start_channel'] - 1
            channels = fixture['channels']
            
            r, g, b = self.current_colors[i]
            
            # Gentle intensity modulation with beat response
            beat_boost = 0
            if beat_occurred:
                time_since_beat = current_time - self.last_beat_time
                if time_since_beat < settings['beat_flash_duration']:
                    beat_boost = settings['beat_response'] * (1 - time_since_beat / settings['beat_flash_duration'])
            
            brightness = min(1.0, intensity * settings['brightness_base'] + beat_boost)
            
            # Set DMX values
            if 'dimmer' in channels:
                data[base_channel + channels['dimmer']] = int(brightness * 255)
                scale = 1.0
            else:
                scale = brightness
            
            if 'red' in channels:
                data[base_channel + channels['red']] = int(r * scale)
            if 'green' in channels:
                data[base_channel + channels['green']] = int(g * scale)
            if 'blue' in channels:
                data[base_channel + channels['blue']] = int(b * scale)
        
        return data
    
    def _compute_rapid_frame(self):
        """Compute DMX frame for rapid beat-sync mode."""
        data = array.array('B', [0] * config.DMX_CHANNELS)
        settings = self.mode_settings
        
        # Get current audio state
        audio_state = self.audio_analyzer.get_state()
        intensity = audio_state['intensity']
        audio_active = audio_state['audio_active']
        
        if not audio_active:
            return data
        
        # Process beat events
        beat_occurred = False
        while not self.beat_queue.empty():
            try:
                self.beat_queue.get_nowait()
                beat_occurred = True
                self.last_beat_time = time.time()
            except:
                break
        
        # Rapid beat response
        if beat_occurred:
            self._handle_beat_event()
        
        # Get color palette (use extended palette for variety)
        colors = config.SMOOTH_COLOR_PALETTE if self.current_mode == "rapid" else config.COLOR_PRESETS
        color = colors[self.current_color_index % len(colors)]
        
        # Process each PAR light with rapid changes
        for i, fixture in enumerate(config.LIGHT_FIXTURES):
            base_channel = fixture['start_channel'] - 1
            channels = fixture['channels']
            
            # Strong beat flash effect
            flash_active = (time.time() - self.beat_flash_time[i]) < settings['beat_flash_duration']
            
            if settings['alternating']:
                light_active = self.lights_on[i]
            else:
                light_active = True
            
            if light_active:
                # Rapid intensity changes
                if flash_active:
                    brightness = 255
                else:
                    brightness = int(intensity * 255 * settings['brightness_base'])
                
                if 'dimmer' in channels:
                    data[base_channel + channels['dimmer']] = brightness
                    scale = 1.0
                else:
                    scale = brightness / 255.0
                
                # Use different colors for each light in rapid mode
                if settings['alternating'] and i > 0:
                    offset_color = colors[(self.current_color_index + i) % len(colors)]
                    r, g, b = offset_color
                else:
                    r, g, b = color
                
                if 'red' in channels:
                    data[base_channel + channels['red']] = int(r * scale)
                if 'green' in channels:
                    data[base_channel + channels['green']] = int(g * scale)
                if 'blue' in channels:
                    data[base_channel + channels['blue']] = int(b * scale)
                
                # Strong strobe on beat
                if 'strobe' in channels and flash_active:
                    data[base_channel + channels['strobe']] = 255
        
        return data
    
    def _compute_classic_frame(self):
        """Compute DMX frame for classic mode (original behavior)."""
        data = array.array('B', [0] * config.DMX_CHANNELS)
        settings = self.mode_settings
        
        # Get current audio state
        audio_state = self.audio_analyzer.get_state()
        intensity = audio_state['intensity']
        audio_active = audio_state['audio_active']
        
        if not audio_active:
            return data
        
        # Process beat events
        beat_occurred = False
        while not self.beat_queue.empty():
            try:
                self.beat_queue.get_nowait()
                beat_occurred = True
                self.last_beat_time = time.time()
            except:
                break
        
        if beat_occurred:
            self._handle_beat_event()
        
        color = config.COLOR_PRESETS[self.current_color_index]
        
        # Process each PAR light
        for i, fixture in enumerate(config.LIGHT_FIXTURES):
            base_channel = fixture['start_channel'] - 1
            channels = fixture['channels']
            
            flash_active = (time.time() - self.beat_flash_time[i]) < settings['beat_flash_duration']
            
            if flash_active:
                brightness = 255
            else:
                brightness = int(intensity * 255 * settings['brightness_base'])
            
            if settings['alternating']:
                light_active = self.lights_on[i]
            else:
                light_active = True
            
            if light_active:
                if 'dimmer' in channels:
                    data[base_channel + channels['dimmer']] = brightness
                    scale = 1.0
                else:
                    scale = brightness / 255.0
                
                if 'red' in channels:
                    data[base_channel + channels['red']] = int(color[0] * scale)
                if 'green' in channels:
                    data[base_channel + channels['green']] = int(color[1] * scale)
                if 'blue' in channels:
                    data[base_channel + channels['blue']] = int(color[2] * scale)
        
        return data
    
    def _handle_beat_event(self):
        """Process a beat event - update colors and light states."""
        settings = self.mode_settings
        
        # Cycle colors if enabled
        if settings['color_cycle_on_beat']:
            self.current_color_index = (self.current_color_index + 1) % len(config.COLOR_PRESETS)
        
        # Handle alternating mode
        if settings['alternating']:
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