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
        # Start with diverse colors instead of all black/red
        initial_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), 
                         (255, 0, 255), (0, 255, 255), (255, 128, 0), (128, 0, 255)]
        self.target_colors = [initial_colors[i % len(initial_colors)] for i in range(config.MAX_LIGHTS)]
        self.current_colors = [initial_colors[i % len(initial_colors)] for i in range(config.MAX_LIGHTS)]
        self.color_fade_progress = [0.0] * config.MAX_LIGHTS  # Fade progress for each PAR
        self.last_color_change = 0
        self.color_phases = [i * 0.2 for i in range(config.MAX_LIGHTS)]  # Phase offset for smooth waves
        
        # Control parameters - more responsive defaults
        self.smoothness = 0.5  # More balanced transitions
        self.rainbow_level = 0.5  # More color diversity
        self.brightness_control = 0.5  # Default midpoint (0.0 = dim, 1.0 = full)
        self.strobe_level = 0.0  # Default off (0.0 = off, 1.0 = max)
        self.beat_sensitivity = 0.5  # More beat response
        self.mood_match = False  # Default off - intensity-based color temperature
        self.pattern = "wave"  # Default to wave pattern for motion
        self.bpm_sync = 1.0  # BPM sync percentage (0.25 = 25% speed, 1.0 = 100%, 2.0 = 200%)
        
        # New controls
        self.frequency_mode = False  # Frequency-based colors
        self.color_theme = 'default'  # Color palette theme
        self.effect_mode = 'none'  # Special effect
        self.echo_enabled = False  # Trail effect
        self.echo_length = 0.5  # Trail length (0-2 seconds)
        self.chaos_level = 0.0  # Randomization (0-1)
        self.ambient_mode = False  # Chill mode
        self.genre_auto = False  # Auto genre adaptation
        
        # Echo/trail state
        self.echo_buffer = []  # Previous frames for trail effect
        self.max_echo_frames = 60  # Max trail frames (2 seconds at 30fps)
        
        # Effect state
        self.effect_phase = 0.0  # Phase for cyclic effects
        self.sparkle_positions = [0] * config.MAX_LIGHTS
        self.chase_position = 0
        self.swell_phase = 0.0  # Phase for swell pattern
        self.spectrum_mode = False  # Pure volume/frequency mode (no beat)
        
        # Chaos state
        self.chaos_colors = [(255,255,255)] * config.MAX_LIGHTS
        self.chaos_pattern_timer = 0
        
        self.control_lock = threading.Lock()
        
        # Initialize colors
        self._initialize_colors()
        
        # DMX frame update interval (milliseconds)
        self.update_interval = int(1000 / config.UPDATE_FPS)
        
    def _initialize_colors(self, already_locked=False):
        """Initialize starting colors based on rainbow level."""
        # Only acquire lock if not already held
        if already_locked:
            self._do_initialize_colors()
        else:
            if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
                try:
                    self._do_initialize_colors()
                finally:
                    self.control_lock.release()
    
    def _do_initialize_colors(self):
        """Actually initialize colors (assumes lock is held)."""
        # Use selected color theme
        palette = config.COLOR_THEMES.get(self.color_theme, config.SMOOTH_COLOR_PALETTE)
        palette_size = len(palette) if palette else 1
        
        # Distribute colors across lights based on rainbow level
        for i in range(config.MAX_LIGHTS):
            if i < self.active_lights:
                if self.rainbow_level < 0.2:
                    # Single color mode - cycle through palette slowly
                    idx = 0
                else:
                    # Spread colors based on rainbow level
                    # Higher rainbow = more diversity
                    step = max(1, int(palette_size * self.rainbow_level / max(1, self.active_lights)))
                    idx = (i * step) % palette_size
                
                color = palette[idx] if idx < len(palette) else palette[0]
                self.target_colors[i] = color
                self.current_colors[i] = color
            else:
                # Inactive lights stay off
                self.target_colors[i] = (0, 0, 0)
                self.current_colors[i] = (0, 0, 0)
    
    def start(self):
        """Start the DMX control thread."""
        self.thread = threading.Thread(target=self._dmx_loop, daemon=True)
        self.thread.start()
    
    def set_smoothness(self, value):
        """Set the smoothness level (0.0 = fast, 1.0 = very smooth)."""
        # Try to acquire lock with timeout to prevent deadlock
        if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
            try:
                self.smoothness = max(0.0, min(1.0, value))
            finally:
                self.control_lock.release()
    
    def set_rainbow_level(self, value):
        """Set the rainbow diversity level (0.0 = single color, 1.0 = full rainbow)."""
        # Try to acquire lock with timeout to prevent deadlock
        if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
            try:
                self.rainbow_level = max(0.0, min(1.0, value))
                # Don't update colors here - let the main loop handle it
            finally:
                self.control_lock.release()
        else:
            # If we can't get the lock, just skip this update
            pass
    
    def set_brightness(self, value):
        """Set the master brightness level (0.0 = dim, 1.0 = full brightness)."""
        # Try to acquire lock with timeout to prevent deadlock
        if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
            try:
                self.brightness_control = max(0.0, min(1.0, value))
            finally:
                self.control_lock.release()
    
    def set_strobe_level(self, value):
        """Set the strobe intensity (0.0 = off, 1.0 = max)."""
        # Try to acquire lock with timeout to prevent deadlock
        if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
            try:
                self.strobe_level = max(0.0, min(1.0, value))
            finally:
                self.control_lock.release()
    
    def set_beat_sensitivity(self, value):
        """Set the beat sensitivity (0.0 = subtle, 1.0 = intense reactions)."""
        # Try to acquire lock with timeout to prevent deadlock
        if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
            try:
                self.beat_sensitivity = max(0.0, min(1.0, value))
            finally:
                self.control_lock.release()
    
    def set_mood_match(self, enabled):
        """Enable/disable mood matching (cool colors for low intensity, warm for high)."""
        # Try to acquire lock with timeout to prevent deadlock
        if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
            try:
                self.mood_match = bool(enabled)
            finally:
                self.control_lock.release()
    
    def set_frequency_mode(self, enabled):
        """Enable/disable frequency-based color mapping."""
        if self.control_lock.acquire(timeout=0.01):
            try:
                self.frequency_mode = bool(enabled)
            finally:
                self.control_lock.release()
    
    def set_color_theme(self, theme_name):
        """Set the color palette theme."""
        if theme_name in config.COLOR_THEMES:
            if self.control_lock.acquire(timeout=0.01):
                try:
                    self.color_theme = theme_name
                    self._do_initialize_colors()  # Call directly since we already have the lock
                finally:
                    self.control_lock.release()
    
    def set_effect_mode(self, effect_name):
        """Set the special effect mode."""
        valid_effects = ['none', 'breathe', 'sparkle', 'chase', 'pulse', 'sweep', 'firefly']
        if effect_name in valid_effects:
            if self.control_lock.acquire(timeout=0.01):
                try:
                    self.effect_mode = effect_name
                    self.effect_phase = 0.0
                finally:
                    self.control_lock.release()
    
    def set_echo_enabled(self, enabled):
        """Enable/disable echo trail effect."""
        if self.control_lock.acquire(timeout=0.01):
            try:
                self.echo_enabled = bool(enabled)
                if not enabled:
                    self.echo_buffer.clear()
            finally:
                self.control_lock.release()
    
    def set_echo_length(self, value):
        """Set echo trail length (0.0 to 2.0 seconds)."""
        if self.control_lock.acquire(timeout=0.01):
            try:
                self.echo_length = max(0.0, min(2.0, value))
            finally:
                self.control_lock.release()
    
    def set_chaos_level(self, value):
        """Set chaos/randomization level (0.0 to 1.0)."""
        if self.control_lock.acquire(timeout=0.01):
            try:
                self.chaos_level = max(0.0, min(1.0, value))
            finally:
                self.control_lock.release()
    
    def set_ambient_mode(self, enabled):
        """Enable/disable ambient chill mode."""
        if self.control_lock.acquire(timeout=0.01):
            try:
                self.ambient_mode = bool(enabled)
            finally:
                self.control_lock.release()
    
    def set_genre_auto(self, enabled):
        """Enable/disable automatic genre adaptation."""
        if self.control_lock.acquire(timeout=0.01):
            try:
                self.genre_auto = bool(enabled)
            finally:
                self.control_lock.release()
    
    def set_spectrum_mode(self, enabled):
        """Enable/disable spectrum mode (pure volume/frequency response, no beat)."""
        if self.control_lock.acquire(timeout=0.01):
            try:
                self.spectrum_mode = bool(enabled)
            finally:
                self.control_lock.release()
    
    def set_bpm_sync(self, value):
        """Set BPM sync percentage (0.25 = 25% speed, 1.0 = 100%, 2.0 = 200%)."""
        if self.control_lock.acquire(timeout=0.01):
            try:
                self.bpm_sync = max(0.1, min(2.0, value))
            finally:
                self.control_lock.release()
    
    def set_pattern(self, pattern_name):
        """Set the lighting pattern (sync, wave, center, alternate, mirror, swell)."""
        valid_patterns = ["sync", "wave", "center", "alternate", "mirror", "swell"]
        if pattern_name in valid_patterns:
            # Try to acquire lock with timeout to prevent deadlock
            if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
                try:
                    self.pattern = pattern_name
                    if pattern_name == 'swell':
                        # Initialize swell phase
                        self.swell_phase = 0.0
                finally:
                    self.control_lock.release()
    
    def set_light_count(self, count):
        """Set the number of active lights."""
        new_count = max(1, min(count, config.MAX_LIGHTS))
        needs_reinit = False
        # Try to acquire lock with timeout to prevent deadlock
        if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
            try:
                if self.active_lights != new_count:
                    self.active_lights = new_count
                    needs_reinit = True
            finally:
                self.control_lock.release()
        
        # Reinitialize colors outside the lock if count changed
        if needs_reinit:
            self._initialize_colors()
    
    def reset(self):
        """Reset controller to default state."""
        if self.control_lock.acquire(timeout=0.1):  # Longer timeout for reset
            try:
                # Reset all parameters to defaults
                self.smoothness = 0.5
                self.rainbow_level = 0.5
                self.brightness_control = 0.5
                self.strobe_level = 0.0
                self.beat_sensitivity = 0.5
                self.bpm_sync = 1.0
                self.mood_match = False
                self.pattern = "wave"
                self.frequency_mode = False
                self.color_theme = 'default'
                self.effect_mode = 'none'
                self.echo_enabled = False
                self.echo_length = 0.5
                self.chaos_level = 0.0
                self.ambient_mode = False
                self.genre_auto = False
                self.spectrum_mode = False
                self.active_lights = config.DEFAULT_LIGHT_COUNT
                
                # Clear buffers
                self.echo_buffer.clear()
                self.effect_phase = 0.0
                self.swell_phase = 0.0
                
                # Reinitialize colors
                self._do_initialize_colors()
            finally:
                self.control_lock.release()
    
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
    
    def _apply_frequency_colors(self, r, g, b, audio_state):
        """Map frequency content to colors."""
        if not self.frequency_mode:
            return r, g, b
            
        # Bass = Red, Mids = Green, Highs = Blue/White
        bass = audio_state.get('bass', 0)
        mid = audio_state.get('mid', 0)
        high = audio_state.get('high', 0)
        
        # Blend with existing colors
        r = int(r * 0.3 + bass * 255 * 0.7)
        g = int(g * 0.3 + mid * 255 * 0.7)
        b = int(b * 0.3 + high * 255 * 0.7)
        
        return min(255, r), min(255, g), min(255, b)
    
    def _apply_spectrum_colors(self, audio_state):
        """Generate colors purely from frequency spectrum (spectrum mode)."""
        bass = audio_state.get('bass', 0)
        mid = audio_state.get('mid', 0)
        high = audio_state.get('high', 0)
        
        # Map frequencies directly to RGB
        # Bass drives warm colors (red/orange)
        # Mid drives green/yellow
        # High drives blue/purple
        
        # Create a color based on frequency balance
        r = int(255 * (bass * 0.8 + mid * 0.2))
        g = int(255 * (mid * 0.7 + bass * 0.2 + high * 0.1))
        b = int(255 * (high * 0.8 + mid * 0.2))
        
        # Ensure minimum brightness
        if r + g + b < 100:
            r = max(40, r)
            g = max(40, g)
            b = max(40, b)
        
        return min(255, r), min(255, g), min(255, b)
    
    def _apply_special_effect(self, r, g, b, light_index, current_time, intensity):
        """Apply special effects to colors."""
        if self.effect_mode == 'none':
            return r, g, b
            
        elif self.effect_mode == 'breathe':
            # Gentle breathing effect
            breathe_speed = 0.5 if not self.ambient_mode else 0.2
            breathe = (math.sin(current_time * breathe_speed) + 1) / 2
            factor = 0.5 + breathe * 0.5
            r, g, b = int(r * factor), int(g * factor), int(b * factor)
            
        elif self.effect_mode == 'sparkle':
            # Random white sparkles
            if random.random() < 0.05 * (1 + intensity):
                if random.randint(0, self.active_lights - 1) == light_index:
                    r, g, b = 255, 255, 255
                    
        elif self.effect_mode == 'chase':
            # Single color chases around
            chase_speed = 2.0 if not self.ambient_mode else 0.5
            chase_pos = int((current_time * chase_speed) % self.active_lights)
            if chase_pos == light_index:
                r, g, b = min(255, r * 2), min(255, g * 2), min(255, b * 2)
            else:
                r, g, b = int(r * 0.3), int(g * 0.3), int(b * 0.3)
                
        elif self.effect_mode == 'pulse':
            # All lights pulse together on beat
            pulse_factor = 1.0 + self.beat_sensitivity * 0.5
            if self.last_beat_time and (current_time - self.last_beat_time) < 0.1:
                r, g, b = min(255, int(r * pulse_factor)), min(255, int(g * pulse_factor)), min(255, int(b * pulse_factor))
                
        elif self.effect_mode == 'sweep':
            # Continuous color sweep
            sweep_speed = 1.0 if not self.ambient_mode else 0.3
            sweep_phase = (current_time * sweep_speed + light_index * 0.2) % 1.0
            hue_shift = int(sweep_phase * 360)
            # Simple HSV to RGB conversion would go here
            # For now, just rotate through R,G,B
            if sweep_phase < 0.33:
                r, g, b = 255, int(sweep_phase * 3 * 255), 0
            elif sweep_phase < 0.66:
                r, g, b = int((1 - (sweep_phase - 0.33) * 3) * 255), 255, 0
            else:
                r, g, b = 0, int((1 - (sweep_phase - 0.66) * 3) * 255), 255
                
        elif self.effect_mode == 'firefly':
            # Gentle random twinkles
            if not hasattr(self, 'firefly_states'):
                self.firefly_states = [0] * config.MAX_LIGHTS
            
            # Random chance to start twinkling
            if random.random() < 0.01:
                self.firefly_states[light_index] = 1.0
                
            # Apply and fade twinkle
            if self.firefly_states[light_index] > 0:
                twinkle = self.firefly_states[light_index]
                r = min(255, int(r + (255 - r) * twinkle))
                g = min(255, int(g + (255 - g) * twinkle))
                b = min(255, int(b + (255 - b) * twinkle))
                self.firefly_states[light_index] *= 0.95  # Fade out
                
        return r, g, b
    
    def _apply_chaos(self, r, g, b, light_index, beat_occurred):
        """Apply chaos/randomization."""
        if self.chaos_level <= 0:
            return r, g, b
            
        # Random color changes
        if random.random() < self.chaos_level * 0.1:
            self.chaos_colors[light_index] = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
            
        # Blend with chaos color
        chaos_r, chaos_g, chaos_b = self.chaos_colors[light_index]
        blend = self.chaos_level * 0.5
        r = int(r * (1 - blend) + chaos_r * blend)
        g = int(g * (1 - blend) + chaos_g * blend)
        b = int(b * (1 - blend) + chaos_b * blend)
        
        # Random pattern switching
        if beat_occurred and random.random() < self.chaos_level * 0.05:
            patterns = ["sync", "wave", "center", "alternate", "mirror"]
            self.pattern = random.choice(patterns)
            
        return r, g, b
    
    def _apply_genre_adaptation(self, audio_state):
        """Adapt settings based on detected genre."""
        if not self.genre_auto:
            return
            
        genre = audio_state.get('genre', 'auto')
        
        if genre == 'edm':
            # Fast, intense, strobing
            self.smoothness = 0.2
            self.beat_sensitivity = 0.8
            self.strobe_level = 0.3
        elif genre == 'hiphop':
            # Strong beats, moderate speed
            self.smoothness = 0.4
            self.beat_sensitivity = 0.9
            self.rainbow_level = 0.3
        elif genre == 'rock':
            # Warm colors, moderate response
            self.smoothness = 0.5
            self.beat_sensitivity = 0.6
            if self.color_theme == 'default':
                self.color_theme = 'warm'
        elif genre == 'jazz':
            # Smooth, sophisticated
            self.smoothness = 0.8
            self.beat_sensitivity = 0.3
            self.rainbow_level = 0.2
        elif genre == 'ambient':
            # Ultra smooth, minimal beat response
            self.smoothness = 0.95
            self.beat_sensitivity = 0.1
            self.ambient_mode = True
    
    def _compute_dmx_frame(self):
        """Compute the DMX channel values for current frame."""
        data = array.array('B', [0] * config.DMX_CHANNELS)
        
        # Get current audio state
        audio_state = self.audio_analyzer.get_state()
        intensity = audio_state['intensity']
        audio_active = audio_state['audio_active']
        
        # Ambient mode - ignore audio activity check
        if not self.ambient_mode and not audio_active:
            return data
            
        # Apply genre adaptation
        self._apply_genre_adaptation(audio_state)
        
        # Handle build-up/drop detection
        if audio_state.get('is_drop', False):
            # EXPLOSION! Max everything briefly
            self.beat_sensitivity = 1.0
            self.strobe_level = 0.5
        
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
            
            # Multi-layer effects system
            # Layer 1: Base pattern-based color selection
            r, g, b = self._apply_pattern(i, current_time)
            
            # Layer 2: Frequency-based colors
            if self.spectrum_mode:
                # In spectrum mode, colors are purely frequency-driven
                r, g, b = self._apply_spectrum_colors(audio_state)
            else:
                r, g, b = self._apply_frequency_colors(r, g, b, audio_state)
            
            # Layer 3: Mood matching (temperature adjustment)
            if self.mood_match:
                r, g, b = self._apply_mood_adjustment(r, g, b, intensity)
            
            # Layer 4: Special effects
            r, g, b = self._apply_special_effect(r, g, b, i, current_time, intensity)
            
            # Layer 5: Chaos randomization
            r, g, b = self._apply_chaos(r, g, b, i, beat_occurred)
            
            # Calculate brightness based on mode
            if self.spectrum_mode:
                # Spectrum mode: pure volume/frequency response, no beat
                # Use frequency bands for brightness modulation
                bass = audio_state.get('bass', 0)
                mid = audio_state.get('mid', 0)
                high = audio_state.get('high', 0)
                
                # Weight the frequencies for overall brightness
                freq_brightness = (bass * 0.5 + mid * 0.3 + high * 0.2)
                brightness = min(1.0, freq_brightness * settings['brightness_base'])
                beat_boost = 0
                
            elif self.pattern == "swell":
                # Swell pattern: synchronized undulation
                # Update swell phase
                swell_speed = 0.1 + (1.0 - self.smoothness) * 0.5  # 0.1 to 0.6 Hz
                self.swell_phase += swell_speed * (1.0 / config.UPDATE_FPS)
                
                # Create slow, deep undulation
                swell_factor = (math.sin(self.swell_phase * 2 * 3.14159) + 1.0) / 2.0
                
                # Combine with intensity for reactive undulation
                base_brightness = 0.2 + intensity * 0.5  # 20% to 70% base
                swell_brightness = base_brightness + swell_factor * 0.3  # Add 0-30% swell
                
                brightness = min(1.0, swell_brightness * settings['brightness_base'])
                beat_boost = 0
                
            else:
                # Normal beat-based brightness
                beat_boost = 0
                if beat_occurred and not self.spectrum_mode:
                    time_since_beat = current_time - self.last_beat_time
                    
                    # Beat flash duration based on smoothness and sensitivity
                    base_duration = settings['beat_flash_duration']
                    if self.smoothness < 0.5:
                        # Fast: 0.1 to 0.3 seconds
                        beat_duration = base_duration * (0.2 + self.smoothness * 1.6)
                    else:
                        # Slow: 0.3 to 2.0 seconds  
                        beat_duration = base_duration * (1.0 + (self.smoothness - 0.5) * 6.0)
                    
                    # Extend duration based on beat sensitivity
                    beat_duration *= (0.5 + self.beat_sensitivity * 1.5)  # 0.5x to 2x duration
                    
                    if time_since_beat < beat_duration:
                        # Beat response intensity controlled by beat_sensitivity
                        # Sensitivity ranges from 0.05 (5% boost) to 0.8 (80% boost)
                        base_response = 0.05 + (self.beat_sensitivity * 0.75)
                        
                        # Modulate by smoothness
                        if self.smoothness < 0.5:
                            # Fast mode: stronger response
                            beat_response = base_response * (1.0 - self.smoothness * 0.3)
                        else:
                            # Smooth mode: gentler response  
                            beat_response = base_response * (0.7 - (self.smoothness - 0.5) * 0.4)
                        
                        beat_boost = beat_response * (1 - time_since_beat / beat_duration)
                
                # Apply master brightness control with beat sensitivity boost
                # Intensity response is also affected by beat_sensitivity
                intensity_multiplier = 0.5 + (self.beat_sensitivity * 1.0)  # 0.5x to 1.5x intensity
                brightness = min(1.0, intensity * intensity_multiplier * settings['brightness_base'] + beat_boost)
            
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
            
            # Apply strobe ONLY when explicitly set via strobe control
            if 'strobe' in channels:
                if self.strobe_level > 0.1:  # Only strobe when slider is actively set
                    # Strobe frequency based on strobe level
                    strobe_rate = self.strobe_level * 10  # 0 to 10 Hz
                    if (current_time * strobe_rate) % 1.0 < 0.5:
                        strobe_value = min(255, int(self.strobe_level * 255))
                        data[base_channel + channels['strobe']] = strobe_value
                    else:
                        data[base_channel + channels['strobe']] = 0
                else:
                    # No strobe at all when slider is at/near zero
                    data[base_channel + channels['strobe']] = 0
        
        return data
    
    def _apply_mood_adjustment(self, r, g, b, intensity):
        """Adjust color temperature based on intensity (cool for low, warm for high)."""
        # Intensity ranges from 0.0 to 1.0
        # Low intensity (0.0-0.3) = cool colors (more blue)
        # Mid intensity (0.3-0.7) = neutral
        # High intensity (0.7-1.0) = warm colors (more red/orange)
        
        if intensity < 0.3:
            # Cool mood - enhance blues, reduce reds
            cool_factor = 1.0 - (intensity / 0.3)  # 1.0 at silence, 0.0 at 0.3
            r = int(r * (0.5 + 0.5 * (1.0 - cool_factor)))  # Reduce red 50% to 100%
            g = int(g * (0.7 + 0.3 * (1.0 - cool_factor)))  # Reduce green 70% to 100%
            b = min(255, int(b * (1.0 + cool_factor * 0.5)))  # Boost blue up to 150%
        elif intensity > 0.7:
            # Warm mood - enhance reds/oranges, reduce blues
            warm_factor = (intensity - 0.7) / 0.3  # 0.0 at 0.7, 1.0 at 1.0
            r = min(255, int(r * (1.0 + warm_factor * 0.5)))  # Boost red up to 150%
            g = int(g * (0.8 + 0.2 * (1.0 - warm_factor * 0.5)))  # Slight orange tint
            b = int(b * (0.5 + 0.5 * (1.0 - warm_factor)))  # Reduce blue 50% to 100%
        
        # Ensure values stay in valid range
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        return r, g, b
    
    def _apply_pattern(self, light_index, current_time):
        """Apply pattern-based color selection for each light."""
        if self.pattern == "sync":
            # All lights show same color
            return self.current_colors[light_index]
            
        elif self.pattern == "wave":
            # Colors flow from left to right
            wave_speed = 0.2 + (1.0 - self.smoothness) * 1.0  # Much slower: 0.2 to 1.2 speed
            phase = (current_time * wave_speed + self.color_phases[light_index]) * 2 * 3.14159
            
            # Use sine wave for smooth transitions
            wave_factor = (math.sin(phase) + 1.0) / 2.0  # 0 to 1
            
            # Blend between current and next color in palette
            base_color = self.current_colors[light_index]
            next_idx = (light_index + 1) % max(1, self.active_lights)
            # Ensure we don't go out of bounds
            if next_idx < len(self.current_colors):
                next_color = self.current_colors[next_idx]
            else:
                next_color = self.current_colors[0]  # Wrap to first
            
            r = int(base_color[0] * (1 - wave_factor) + next_color[0] * wave_factor)
            g = int(base_color[1] * (1 - wave_factor) + next_color[1] * wave_factor)
            b = int(base_color[2] * (1 - wave_factor) + next_color[2] * wave_factor)
            
            return (r, g, b)
            
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
                
        elif self.pattern == "swell":
            # Synchronized undulation - all lights move together
            # This will be handled differently in brightness calculation
            # For now, return the same color for all lights with smooth transitions
            return self.current_colors[light_index]
                
        else:
            # Default to sync
            return self.current_colors[light_index]
    
    def _update_colors(self, beat_occurred, intensity):
        """Update color transitions based on rainbow level and beats."""
        if self.control_lock.acquire(timeout=0.01):  # 10ms timeout
            try:
                current_time = time.time()
                
                # Apply BPM sync to timing
                bpm_factor = 1.0 / max(0.1, self.bpm_sync)  # Invert: lower sync = slower changes
                
                # Special timing for swell pattern
                if self.pattern == "swell":
                    change_interval = (5.0 + self.smoothness * 10.0) * bpm_factor  # 5-15 seconds base
                    change_on_beat = False  # No beat triggers for swell
                # Spectrum mode - frequency-driven changes
                elif self.spectrum_mode:
                    change_interval = (3.0 + self.smoothness * 5.0) * bpm_factor  # 3-8 seconds base
                    change_on_beat = False  # No beat triggers in spectrum mode
                # Normal color transitions - MUCH FASTER
                elif self.rainbow_level < 0.2:
                    # Single color mode
                    change_interval = (3.0 + self.smoothness * 5.0) * bpm_factor  # 3-8 seconds
                    change_on_beat = False
                elif self.rainbow_level < 0.5:
                    # Moderate diversity
                    change_interval = (2.0 + self.smoothness * 3.0) * bpm_factor  # 2-5 seconds
                    change_on_beat = beat_occurred and intensity > 0.6
                elif self.rainbow_level < 0.8:
                    # High diversity
                    change_interval = (1.0 + self.smoothness * 2.0) * bpm_factor  # 1-3 seconds
                    change_on_beat = beat_occurred and intensity > 0.4
                else:
                    # Full rainbow - fast changes
                    change_interval = (0.5 + self.smoothness * 1.0) * bpm_factor  # 0.5-1.5 seconds
                    change_on_beat = beat_occurred
                
                # Check if it's time to change colors
                time_to_change = current_time - self.last_color_change > change_interval
                
                if time_to_change or change_on_beat:
                    self.last_color_change = current_time
                    self._select_new_colors()
                
                # Update fade progress for smooth transitions
                self._update_color_fades()
            finally:
                self.control_lock.release()
    
    def _select_new_colors(self):
        """Select new target colors based on rainbow level."""
        try:
            # Use selected color theme
            palette = config.COLOR_THEMES.get(self.color_theme, config.SMOOTH_COLOR_PALETTE)
            palette_size = len(palette)
            
            # Ensure palette has at least one color
            if palette_size == 0:
                palette = [(255, 0, 0)]  # Default to red
                palette_size = 1
            
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
                base_idx = random.randint(0, max(0, palette_size - 1))
                spread = max(1, int(palette_size * 0.3))  # Colors within 30% of palette, minimum 1
                
                for i in range(self.active_lights):
                    offset = i * spread // max(1, self.active_lights)
                    idx = (base_idx + offset) % palette_size
                    self.target_colors[i] = palette[idx]
                    self.color_fade_progress[i] = 0.0
                    
            elif self.rainbow_level < 0.8:
                # High diversity - lights have different colors
                indices = []
                spread = max(1, palette_size // 3)  # Ensure spread is at least 1
                
                for i in range(self.active_lights):
                    # Ensure we don't go negative in random.randint
                    random_offset = random.randint(0, max(0, spread-1))
                    idx = (i * spread + random_offset) % palette_size
                    indices.append(idx)
                
                for i in range(self.active_lights):
                    self.target_colors[i] = palette[indices[i]]
                    self.color_fade_progress[i] = 0.0
                    
            else:
                # Full rainbow - maximum color diversity
                # Each light gets a random color from different parts of palette
                # Ensure we have enough indices for all active lights
                num_colors_needed = min(self.active_lights, palette_size)
                if num_colors_needed <= palette_size:
                    # We have enough colors in palette, sample unique colors
                    indices = random.sample(range(palette_size), num_colors_needed)
                else:
                    # More lights than colors, will need to repeat some
                    indices = list(range(palette_size))
                    random.shuffle(indices)
                
                for i in range(self.active_lights):
                    # Use modulo to handle case where we have more lights than indices
                    idx = indices[i % len(indices)]
                    self.target_colors[i] = palette[idx]
                    self.color_fade_progress[i] = 0.0
                    
        except Exception as e:
            # If any error occurs, just set all lights to a safe default
            print(f"Error in _select_new_colors: {e}")
            for i in range(self.active_lights):
                self.target_colors[i] = (255, 0, 0)  # Default to red
                self.color_fade_progress[i] = 0.0
    
    def _update_color_fades(self):
        """Update the fade progress for color transitions."""
        # Simpler, faster fade speed calculation
        # Apply BPM sync to fade speed too
        bpm_factor = max(0.1, self.bpm_sync)
        
        # Smoothness 0.0 = instant changes
        # Smoothness 0.5 = balanced (0.5 second fade)
        # Smoothness 1.0 = slow (2 second fade)
        fade_time = 0.1 + self.smoothness * 1.9  # 0.1 to 2.0 seconds
        fade_speed = (1.0 / (fade_time * config.UPDATE_FPS)) * bpm_factor
        
        # Update ALL active lights, not just 3
        for i in range(self.active_lights):
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