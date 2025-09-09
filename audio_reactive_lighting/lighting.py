"""
DMX lighting control module for managing PAR lights via OLA.
"""

import array
import threading
import time
import math
import random
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
        self.beat_flash_time = [0, 0, 0]  # Track flash timing for each PAR
        self.last_beat_time = 0
        
        # Color state for smooth transitions
        self.target_colors = [(0, 0, 0)] * 3  # Target colors for each PAR
        self.current_colors = [(0, 0, 0)] * 3  # Current colors for smooth fading
        self.color_fade_progress = [0.0] * 3  # Fade progress for each PAR
        self.last_color_change = 0
        
        # Control parameters - defaults for relaxing smooth waves
        self.smoothness = 0.75  # Default to smooth transitions (0.0 = fast, 1.0 = very smooth)
        self.rainbow_level = 0.3  # Gentle color diversity (0.0 = single color, 1.0 = full rainbow)
        self.brightness_control = 0.6  # Master brightness control (0.0 = dim, 1.0 = full)
        self.strobe_level = 0.0  # Default off (0.0 = off, 1.0 = max)
        self.pattern = "wave"  # Default to wave pattern for flowing effect
        self.control_lock = threading.Lock()
        
        # Initialize colors
        self._initialize_colors()
        
        # DMX frame update interval (milliseconds)
        self.update_interval = int(1000 / config.UPDATE_FPS)
        
    def _initialize_colors(self):
        """Initialize starting colors based on rainbow level."""
        with self.control_lock:
            palette = config.SMOOTH_COLOR_PALETTE
            
            if self.rainbow_level < 0.2:
                # Single color mode - all lights same color
                color = palette[0]
                for i in range(3):
                    self.target_colors[i] = color
                    self.current_colors[i] = color
            else:
                # Diverse colors - spread across palette
                palette_size = len(palette)
                spread = int(palette_size * self.rainbow_level / 3)
                for i in range(3):
                    idx = (i * spread) % palette_size
                    self.target_colors[i] = palette[idx]
                    self.current_colors[i] = self.target_colors[i]
    
    def start(self):
        """Start the DMX control thread."""
        self.thread = threading.Thread(target=self._dmx_loop, daemon=True)
        self.thread.start()
    
    def set_smoothness(self, value):
        """Set the smoothness level (0.0 = fast, 1.0 = very smooth)."""
        with self.control_lock:
            self.smoothness = max(0.0, min(1.0, value))
            print(f"Smoothness set to: {self.smoothness:.2f}")
    
    def set_rainbow_level(self, value):
        """Set the rainbow diversity level (0.0 = single color, 1.0 = full rainbow)."""
        with self.control_lock:
            self.rainbow_level = max(0.0, min(1.0, value))
            print(f"Rainbow level set to: {self.rainbow_level:.2f}")
    
    def set_brightness(self, value):
        """Set the master brightness level (0.0 = dim, 1.0 = full brightness)."""
        with self.control_lock:
            self.brightness_control = max(0.0, min(1.0, value))
            print(f"Brightness set to: {self.brightness_control:.2f}")
    
    def set_strobe_level(self, value):
        """Set the strobe intensity (0.0 = off, 1.0 = max)."""
        with self.control_lock:
            self.strobe_level = max(0.0, min(1.0, value))
            print(f"Strobe level set to: {self.strobe_level:.2f}")
    
    def set_pattern(self, pattern_name):
        """Set the lighting pattern (sync, wave, center, alternate, mirror)."""
        valid_patterns = ["sync", "wave", "center", "alternate", "mirror"]
        if pattern_name in valid_patterns:
            with self.control_lock:
                self.pattern = pattern_name
                print(f"Pattern set to: {self.pattern}")
    
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
        data = array.array('B', [0] * config.DMX_CHANNELS)
        
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
        
        # Update colors
        self._update_colors(beat_occurred, intensity)
        
        # Apply colors to DMX channels
        current_time = time.time()
        settings = config.LIGHTING_SETTINGS
        
        for i, fixture in enumerate(config.LIGHT_FIXTURES):
            base_channel = fixture['start_channel'] - 1
            channels = fixture['channels']
            
            # Apply pattern-based color selection
            r, g, b = self._apply_pattern(i, current_time)
            
            # Calculate brightness with beat response
            beat_boost = 0
            if beat_occurred:
                time_since_beat = current_time - self.last_beat_time
                # Beat flash duration affected by smoothness (doubled range)
                # At max smoothness, beat flash is 4x longer than base
                beat_duration = settings['beat_flash_duration'] * (1.0 + self.smoothness * 3.0)
                if time_since_beat < beat_duration:
                    # Beat response intensity affected by smoothness (more gentle at high smoothness)
                    beat_response = settings['beat_response'] * (1.0 - self.smoothness * 0.7)
                    beat_boost = beat_response * (1 - time_since_beat / beat_duration)
            
            # Apply master brightness control on top of calculated brightness
            brightness = min(1.0, intensity * settings['brightness_base'] + beat_boost)
            brightness *= self.brightness_control  # Apply master brightness slider
            
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
            
            # Apply strobe effect on strong beats
            if 'strobe' in channels and self.strobe_level > 0:
                if beat_occurred and intensity > (1.0 - self.strobe_level * 0.5):
                    # Strobe intensity based on slider (0-255)
                    strobe_value = int(self.strobe_level * 255)
                    data[base_channel + channels['strobe']] = strobe_value
                else:
                    data[base_channel + channels['strobe']] = 0
        
        return data
    
    def _apply_pattern(self, light_index, current_time):
        """Apply pattern-based color selection for each light."""
        if self.pattern == "sync":
            # All lights show same color
            return self.current_colors[light_index]
            
        elif self.pattern == "wave":
            # Colors flow from left to right (with doubled smoothness range)
            # At max smoothness, wave is 4x slower than at min
            wave_speed = 0.5 + (1.0 - self.smoothness) * 3.5  # 0.5 to 4.0 speed range
            wave_offset = int((current_time * wave_speed) % 3)
            color_idx = (light_index + wave_offset) % 3
            return self.current_colors[color_idx]
            
        elif self.pattern == "center":
            # Center light leads, outer lights follow
            if light_index == 1:  # Center light (PAR2)
                return self.current_colors[1]
            else:  # Outer lights mirror center with delay
                delay_frames = int(10 * self.smoothness)  # More delay when smoother
                return self.current_colors[1] if delay_frames == 0 else self.current_colors[light_index]
                
        elif self.pattern == "alternate":
            # Lights alternate between two color groups
            beat_phase = int(current_time * 2) % 2
            if light_index == 1:  # Center always active
                return self.current_colors[1]
            elif (light_index == 0 and beat_phase == 0) or (light_index == 2 and beat_phase == 1):
                return self.current_colors[light_index]
            else:
                # Dim the inactive lights
                r, g, b = self.current_colors[light_index]
                dim_factor = 0.3
                return (int(r * dim_factor), int(g * dim_factor), int(b * dim_factor))
                
        elif self.pattern == "mirror":
            # Outer lights mirror each other, center is unique
            if light_index == 1:  # Center light
                return self.current_colors[1]
            else:  # Outer lights use same color
                return self.current_colors[0]
                
        else:
            # Default to sync
            return self.current_colors[light_index]
    
    def _update_colors(self, beat_occurred, intensity):
        """Update color transitions based on rainbow level and beats."""
        with self.control_lock:
            current_time = time.time()
            
            # Determine color change frequency based on rainbow level (with doubled smoothness range)
            if self.rainbow_level < 0.2:
                # Single color mode - change slowly (up to 2x slower)
                change_interval = 8.0 + self.smoothness * 8.0  # 8-16 seconds
                change_on_beat = False
            elif self.rainbow_level < 0.5:
                # Moderate diversity - change occasionally
                change_interval = 4.0 + self.smoothness * 4.0  # 4-8 seconds
                change_on_beat = beat_occurred and intensity > 0.6
            elif self.rainbow_level < 0.8:
                # High diversity - change frequently
                change_interval = 2.0 + self.smoothness * 2.0  # 2-4 seconds
                change_on_beat = beat_occurred and intensity > 0.4
            else:
                # Full rainbow - change on every beat or quickly
                change_interval = 1.0 + self.smoothness * 1.0  # 1-2 seconds
                change_on_beat = beat_occurred
            
            # Check if it's time to change colors
            time_to_change = current_time - self.last_color_change > change_interval
            
            if time_to_change or change_on_beat:
                self.last_color_change = current_time
                self._select_new_colors()
            
            # Update fade progress for smooth transitions
            self._update_color_fades()
    
    def _select_new_colors(self):
        """Select new target colors based on rainbow level."""
        palette = config.SMOOTH_COLOR_PALETTE
        palette_size = len(palette)
        
        if self.rainbow_level < 0.2:
            # Single color mode - all lights same color
            # Move to next color in palette
            current_idx = 0
            for color in palette:
                if color == self.target_colors[0]:
                    current_idx = palette.index(color)
                    break
            next_idx = (current_idx + 1) % palette_size
            new_color = palette[next_idx]
            
            for i in range(3):
                self.target_colors[i] = new_color
                self.color_fade_progress[i] = 0.0
                
        elif self.rainbow_level < 0.5:
            # Moderate diversity - lights have related colors
            base_idx = random.randint(0, palette_size - 1)
            spread = int(palette_size * 0.3)  # Colors within 30% of palette
            
            for i in range(3):
                offset = i * spread // 3
                idx = (base_idx + offset) % palette_size
                self.target_colors[i] = palette[idx]
                self.color_fade_progress[i] = 0.0
                
        elif self.rainbow_level < 0.8:
            # High diversity - lights have different colors
            indices = []
            spread = palette_size // 3
            
            for i in range(3):
                idx = (i * spread + random.randint(0, spread-1)) % palette_size
                indices.append(idx)
            
            for i in range(3):
                self.target_colors[i] = palette[indices[i]]
                self.color_fade_progress[i] = 0.0
                
        else:
            # Full rainbow - maximum color diversity
            # Each light gets a random color from different parts of palette
            indices = random.sample(range(palette_size), min(3, palette_size))
            
            for i in range(3):
                self.target_colors[i] = palette[indices[i]]
                self.color_fade_progress[i] = 0.0
    
    def _update_color_fades(self):
        """Update the fade progress for color transitions."""
        # Calculate fade speed based on smoothness (ultra smooth range)
        # Smoothness 0.0 = instant (fade_speed = 1.0)
        # Smoothness 0.5 = slow (fade_speed = ~0.008)
        # Smoothness 0.75 = very slow (fade_speed = ~0.004) - default
        # Smoothness 1.0 = ultra slow (fade_speed = 0.001) - extremely gentle
        fade_speed = 0.001 + (1.0 - self.smoothness) * 0.999
        
        for i in range(3):
            if self.color_fade_progress[i] < 1.0:
                self.color_fade_progress[i] = min(1.0, self.color_fade_progress[i] + fade_speed)
                
                # Interpolate between current and target colors
                r_current, g_current, b_current = self.current_colors[i]
                r_target, g_target, b_target = self.target_colors[i]
                
                progress = self.color_fade_progress[i]
                # Smooth ease-in-out interpolation
                smooth_progress = 0.5 - 0.5 * math.cos(progress * math.pi)
                
                self.current_colors[i] = (
                    int(r_current + (r_target - r_current) * smooth_progress),
                    int(g_current + (g_target - g_current) * smooth_progress),
                    int(b_current + (b_target - b_current) * smooth_progress)
                )
    
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