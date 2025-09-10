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
        
        # Light count configuration
        self.active_lights = config.DEFAULT_LIGHT_COUNT
        
        # Lighting state (sized for max lights)
        self.current_color_index = 0
        self.beat_flash_time = [0] * config.MAX_LIGHTS  # Track flash timing for each PAR
        self.last_beat_time = 0
        
        # Color state for smooth transitions (sized for max lights)
        self.target_colors = [(0, 0, 0)] * config.MAX_LIGHTS  # Target colors for each PAR
        self.current_colors = [(0, 0, 0)] * config.MAX_LIGHTS  # Current colors for smooth fading
        self.color_fade_progress = [0.0] * config.MAX_LIGHTS  # Fade progress for each PAR
        self.last_color_change = 0
        
        # Control parameters - midpoint defaults for balanced effect
        self.smoothness = 0.5  # Default midpoint (0.0 = fast, 1.0 = very smooth)
        self.rainbow_level = 0.5  # Default midpoint (0.0 = single color, 1.0 = full rainbow)
        self.brightness_control = 0.5  # Default midpoint (0.0 = dim, 1.0 = full)
        self.strobe_level = 0.0  # Default off (0.0 = off, 1.0 = max)
        self.pattern = "sync"  # Default to sync pattern
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
                for i in range(self.active_lights):
                    self.target_colors[i] = color
                    self.current_colors[i] = color
            else:
                # Diverse colors - spread across palette
                palette_size = len(palette)
                spread = int(palette_size * self.rainbow_level / max(3, self.active_lights))
                for i in range(self.active_lights):
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
            # Remove print to avoid I/O blocking while holding lock
    
    def set_rainbow_level(self, value):
        """Set the rainbow diversity level (0.0 = single color, 1.0 = full rainbow)."""
        with self.control_lock:
            self.rainbow_level = max(0.0, min(1.0, value))
            # Remove print to avoid I/O blocking while holding lock
    
    def set_brightness(self, value):
        """Set the master brightness level (0.0 = dim, 1.0 = full brightness)."""
        with self.control_lock:
            self.brightness_control = max(0.0, min(1.0, value))
            # Remove print to avoid I/O blocking while holding lock
    
    def set_strobe_level(self, value):
        """Set the strobe intensity (0.0 = off, 1.0 = max)."""
        with self.control_lock:
            self.strobe_level = max(0.0, min(1.0, value))
            # Remove print to avoid I/O blocking while holding lock
    
    def set_pattern(self, pattern_name):
        """Set the lighting pattern (sync, wave, center, alternate, mirror)."""
        valid_patterns = ["sync", "wave", "center", "alternate", "mirror"]
        if pattern_name in valid_patterns:
            with self.control_lock:
                self.pattern = pattern_name
                # Remove print to avoid I/O blocking while holding lock
    
    def set_light_count(self, count):
        """Set the number of active lights."""
        new_count = max(1, min(count, config.MAX_LIGHTS))
        with self.control_lock:
            if self.active_lights != new_count:
                self.active_lights = new_count
                # Remove print to avoid I/O blocking while holding lock
                needs_reinit = True
            else:
                needs_reinit = False
        
        # Reinitialize colors outside the lock if count changed
        if needs_reinit:
            self._initialize_colors()
    
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
        
        # Only process active lights
        for i in range(self.active_lights):
            fixture = config.LIGHT_FIXTURES[i]
            base_channel = fixture['start_channel'] - 1
            channels = fixture['channels']
            
            # Apply pattern-based color selection
            r, g, b = self._apply_pattern(i, current_time)
            
            # Calculate brightness with beat response (expanded range)
            beat_boost = 0
            if beat_occurred:
                time_since_beat = current_time - self.last_beat_time
                
                # Beat flash duration with expanded range
                if self.smoothness < 0.5:
                    # Fast: 0.1 to 0.3 seconds
                    beat_duration = settings['beat_flash_duration'] * (0.2 + self.smoothness * 1.6)
                else:
                    # Slow: 0.3 to 2.0 seconds  
                    beat_duration = settings['beat_flash_duration'] * (1.0 + (self.smoothness - 0.5) * 6.0)
                
                if time_since_beat < beat_duration:
                    # Beat response intensity with expanded range
                    if self.smoothness < 0.5:
                        # Strong: 100% to 60% response
                        beat_response = settings['beat_response'] * (1.0 - self.smoothness * 0.8)
                    else:
                        # Gentle: 60% to 10% response
                        beat_response = settings['beat_response'] * (0.6 - (self.smoothness - 0.5) * 1.0)
                    beat_boost = beat_response * (1 - time_since_beat / beat_duration)
            
            # Apply master brightness control with expanded range
            brightness = min(1.0, intensity * settings['brightness_base'] + beat_boost)
            
            # Expanded brightness range with minimum floor:
            # 0.0 = 5% brightness (very dim but still visible)
            # 0.5 = 100% brightness (normal) 
            # 1.0 = 120% brightness (boosted, clamped to prevent overflow)
            if self.brightness_control < 0.5:
                # Dim range: 5% to 100% (increased minimum from 10% to 5% to prevent total darkness)
                brightness_multiplier = 0.05 + (self.brightness_control * 2 * 0.95)
            else:
                # Boost range: 100% to 120% (reduced from 150% to prevent overflow)
                brightness_multiplier = 1.0 + ((self.brightness_control - 0.5) * 2 * 0.2)
            
            brightness *= brightness_multiplier
            
            # Ensure minimum brightness to prevent complete darkness
            brightness = max(0.01, brightness)
            
            # Clamp brightness to prevent DMX overflow
            brightness = min(1.0, brightness)
            
            # Set DMX values with clamping and minimum floor
            if 'dimmer' in channels:
                # Ensure minimum value of 1 when brightness > 0 to prevent complete darkness
                dimmer_value = int(brightness * 255)
                if dimmer_value > 0:
                    dimmer_value = max(1, dimmer_value)
                data[base_channel + channels['dimmer']] = min(255, dimmer_value)
                scale = 1.0
            else:
                scale = brightness
            
            if 'red' in channels:
                red_value = int(r * scale)
                if red_value > 0:
                    red_value = max(1, red_value)  # Minimum of 1 when not zero
                data[base_channel + channels['red']] = min(255, red_value)
            if 'green' in channels:
                green_value = int(g * scale)
                if green_value > 0:
                    green_value = max(1, green_value)  # Minimum of 1 when not zero
                data[base_channel + channels['green']] = min(255, green_value)
            if 'blue' in channels:
                blue_value = int(b * scale)
                if blue_value > 0:
                    blue_value = max(1, blue_value)  # Minimum of 1 when not zero
                data[base_channel + channels['blue']] = min(255, blue_value)
            
            # Apply strobe effect on strong beats
            if 'strobe' in channels and self.strobe_level > 0:
                if beat_occurred and intensity > (1.0 - self.strobe_level * 0.5):
                    # Strobe intensity based on slider (0-255)
                    strobe_value = min(255, int(self.strobe_level * 255))
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
            # Colors flow from left to right
            wave_speed = 0.5 + (1.0 - self.smoothness) * 3.5  # 0.5 to 4.0 speed range
            wave_offset = int((current_time * wave_speed) % self.active_lights)
            color_idx = (light_index + wave_offset) % self.active_lights
            return self.current_colors[color_idx]
            
        elif self.pattern == "center":
            # Center light(s) lead, outer lights follow
            center_idx = self.active_lights // 2
            if self.active_lights % 2 == 1:
                # Odd number: single center
                if light_index == center_idx:
                    return self.current_colors[center_idx]
            else:
                # Even number: two center lights
                if light_index == center_idx or light_index == center_idx - 1:
                    return self.current_colors[light_index]
            
            # Outer lights mirror center with delay
            delay_frames = int(10 * self.smoothness)
            return self.current_colors[center_idx] if delay_frames == 0 else self.current_colors[light_index]
                
        elif self.pattern == "alternate":
            # Lights alternate in groups
            if self.active_lights <= 2:
                # Simple alternation for 1-2 lights
                beat_phase = int(current_time * 2) % 2
                return self.current_colors[light_index] if beat_phase == 0 else (
                    int(self.current_colors[light_index][0] * 0.3),
                    int(self.current_colors[light_index][1] * 0.3),
                    int(self.current_colors[light_index][2] * 0.3)
                )
            else:
                # Group alternation for 3+ lights
                beat_phase = int(current_time * 2) % 2
                group = light_index % 2
                if group == beat_phase:
                    return self.current_colors[light_index]
                else:
                    r, g, b = self.current_colors[light_index]
                    return (int(r * 0.3), int(g * 0.3), int(b * 0.3))
                
        elif self.pattern == "mirror":
            # Lights mirror from center outward
            if self.active_lights == 1:
                return self.current_colors[0]
            
            # Calculate mirror pairs
            mirror_point = self.active_lights / 2.0
            if light_index < mirror_point:
                # Left side
                return self.current_colors[light_index]
            else:
                # Right side mirrors left
                mirror_idx = self.active_lights - 1 - light_index
                return self.current_colors[mirror_idx]
                
        else:
            # Default to sync
            return self.current_colors[light_index]
    
    def _update_colors(self, beat_occurred, intensity):
        """Update color transitions based on rainbow level and beats."""
        with self.control_lock:
            current_time = time.time()
            
            # Determine color change frequency with expanded smoothness range
            if self.rainbow_level < 0.2:
                # Single color mode - change slowly
                if self.smoothness < 0.5:
                    change_interval = 4.0 + self.smoothness * 8.0  # 4-8 seconds (fast)
                else:
                    change_interval = 8.0 + (self.smoothness - 0.5) * 24.0  # 8-20 seconds (slow)
                change_on_beat = False
            elif self.rainbow_level < 0.5:
                # Moderate diversity - change occasionally
                if self.smoothness < 0.5:
                    change_interval = 2.0 + self.smoothness * 4.0  # 2-4 seconds (fast)
                else:
                    change_interval = 4.0 + (self.smoothness - 0.5) * 8.0  # 4-8 seconds (slow)
                change_on_beat = beat_occurred and intensity > 0.6
            elif self.rainbow_level < 0.8:
                # High diversity - change frequently
                if self.smoothness < 0.5:
                    change_interval = 1.0 + self.smoothness * 2.0  # 1-2 seconds (fast)
                else:
                    change_interval = 2.0 + (self.smoothness - 0.5) * 4.0  # 2-4 seconds (slow)
                change_on_beat = beat_occurred and intensity > 0.4
            else:
                # Full rainbow - change on every beat or quickly
                if self.smoothness < 0.5:
                    change_interval = 0.5 + self.smoothness * 1.0  # 0.5-1 seconds (fast)
                else:
                    change_interval = 1.0 + (self.smoothness - 0.5) * 2.0  # 1-2 seconds (slow)
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
            
            for i in range(self.active_lights):
                self.target_colors[i] = new_color
                self.color_fade_progress[i] = 0.0
                
        elif self.rainbow_level < 0.5:
            # Moderate diversity - lights have related colors
            base_idx = random.randint(0, palette_size - 1)
            spread = int(palette_size * 0.3)  # Colors within 30% of palette
            
            for i in range(self.active_lights):
                offset = i * spread // 3
                idx = (base_idx + offset) % palette_size
                self.target_colors[i] = palette[idx]
                self.color_fade_progress[i] = 0.0
                
        elif self.rainbow_level < 0.8:
            # High diversity - lights have different colors
            indices = []
            spread = palette_size // 3
            
            for i in range(self.active_lights):
                idx = (i * spread + random.randint(0, spread-1)) % palette_size
                indices.append(idx)
            
            for i in range(self.active_lights):
                self.target_colors[i] = palette[indices[i]]
                self.color_fade_progress[i] = 0.0
                
        else:
            # Full rainbow - maximum color diversity
            # Each light gets a random color from different parts of palette
            indices = random.sample(range(palette_size), min(3, palette_size))
            
            for i in range(self.active_lights):
                self.target_colors[i] = palette[indices[i]]
                self.color_fade_progress[i] = 0.0
    
    def _update_color_fades(self):
        """Update the fade progress for color transitions."""
        # Calculate fade speed with expanded range (10x range)
        # Smoothness 0.0 = super fast (fade_speed = 2.0) - instant changes
        # Smoothness 0.5 = moderate (fade_speed = ~0.02) - balanced
        # Smoothness 1.0 = ultra slow (fade_speed = 0.0005) - extremely gentle
        if self.smoothness < 0.5:
            # Fast range: 2.0 to 0.02 (100x range)
            fade_speed = 2.0 - (self.smoothness * 2 * 0.99)
        else:
            # Slow range: 0.02 to 0.0005 (40x range)
            fade_speed = 0.02 - ((self.smoothness - 0.5) * 2 * 0.01975)
        
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