"""
Simple mode DMX controller with preset programs.
"""

import array
import math
import random
import time
from collections import deque
from lighting_base import BaseDmxController
import config


class SimpleDmxController(BaseDmxController):
    """Simple mode controller with preset lighting programs."""
    
    # Color palettes - ensuring variety and visibility
    COLORS_FULL = [
        (255, 0, 0),      # Red
        (0, 255, 0),      # Green
        (0, 0, 255),      # Blue
        (255, 255, 0),    # Yellow
        (255, 0, 255),    # Magenta
        (0, 255, 255),    # Cyan
        (255, 128, 0),    # Orange
        (128, 0, 255),    # Purple
        (255, 64, 128),   # Pink
        (0, 255, 128),    # Teal
        (255, 255, 255),  # White
    ]
    
    COLORS_COOL = [
        (0, 255, 0),      # Green
        (0, 0, 255),      # Blue
        (0, 255, 255),    # Cyan
        (128, 0, 255),    # Purple
        (0, 255, 128),    # Teal
        (64, 128, 255),   # Sky Blue
        (255, 255, 255),  # White
        (200, 255, 200),  # Pale Green
        (200, 200, 255),  # Pale Blue
        (255, 255, 0),    # Yellow
    ]
    
    PROGRAMS = [
        "Bounce (Same Color)",
        "Bounce (Different Colors)",
        "Bounce (Discrete)",
        "Swell (Different Colors)",
        "Swell (Same Color)",
        "Disco",
        "Psych",
        "Pulse",
        "Spectrum",
        "Strobe",
        "Chase",
        "Center Burst",
        "VU Meter",
        "Ripple",
        "Alternating",
        "Kaleidoscope",
        "Spiral",
        "Breathing",
        "Interference",
        "Color Ripples",
        "Ripple Bounce",
        "Ripple Bounce Color",
        "DJ Mode",
    ]
    
    def __init__(self, audio_analyzer, beat_queue, stop_event):
        """Initialize simple mode controller."""
        super().__init__(audio_analyzer, beat_queue, stop_event)
        
        # Simple mode controls
        self.program = "Bounce (Same Color)"  # Default program
        self.bpm_division = 1  # 1, 2, 4, 8, or 16 (every Nth beat)
        self.dimming = 1.0  # 0.0 to 1.0 (0% to 100%)
        self.cool_colors_only = False
        
        # Program state
        self.bounce_position = 0
        self.bounce_direction = 1  # 1 = forward, -1 = backward
        self.bounce_color_index = 0
        self.bounce_colors = []  # Current colors for each light
        
        self.swell_phase = 0.0
        self.swell_color_index = 0
        
        self.disco_states = []  # Random states for each light
        self.psych_phase = 0.0
        
        # Enhanced Psych mode state
        self.psych_pattern_type = 0  # Current pattern (0-4)
        self.psych_symmetry_mode = 0  # Mirror, radial, bilateral
        self.psych_color_pairs = []  # Complementary color pairs
        self.psych_phase_offsets = []  # Per-light phase offsets
        self.psych_flicker_states = []  # Flicker intensity per light
        self.psych_spiral_angle = 0.0  # Rotation angle
        self.psych_morph_progress = 0.0  # Color morph progress
        self.psych_pattern_timer = 0  # Time until next pattern change
        self.psych_beat_count = 0  # Beat counter for pattern changes
        
        # New program states
        self.pulse_color_index = 0
        self.spectrum_colors = []  # Colors for spectrum display
        self.strobe_on = False
        self.strobe_color_index = 0
        self.chase_position = 0
        self.chase_color_index = 0
        self.burst_radius = 0
        self.burst_color_index = 0
        self.vu_peak = 0
        self.ripple_positions = []  # Multiple wave positions
        self.alternating_state = False
        self.alternating_color_index = 0
        
        # New pattern generator states
        self.kaleidoscope_angle = 0.0
        self.kaleidoscope_color_index = 0
        self.spiral_position = 0.0
        self.spiral_color_phase = 0.0
        self.breathing_phases = []
        self.interference_phases = []
        self.color_ripple_centers = []  # List of active ripples
        
        # Ripple Bounce states
        self.ripple_bounce_position = 0.0
        self.ripple_bounce_direction = 1  # 1 = forward, -1 = backward
        self.ripple_bounce_color_index = 0
        self.ripple_bounce_trail = []  # Trail positions for smooth effect
        self.ripple_bounce_colors = []  # Colors for each light in color mode
        
        # DJ Mode states
        self.dj_current_program = "Breathing"  # Start with ambient
        self.dj_program_beats = 0  # Beats in current program
        self.dj_min_beats = 16  # Minimum beats before switching
        self.dj_energy_history = []  # Track energy over time
        self.dj_last_switch_time = 0
        self.dj_build_detected = False
        self.dj_drop_countdown = 0
        self.dj_intensity_avg = 0.3  # Running average
        self.dj_bass_avg = 0.3
        self.dj_high_avg = 0.3
        
        # Beat tracking for divisions
        self.beat_counter = 0
        self.last_division_beat = 0
        
        # Initialize per-light states
        self._init_light_states()
        
    def _init_light_states(self):
        """Initialize state arrays for lights."""
        self.bounce_colors = [(255, 0, 0)] * config.MAX_LIGHTS
        self.disco_states = [
            {
                'color': random.choice(self._get_color_palette()),
                'brightness': 0.0,  # Start with lights off
                'fade_speed': 0.01 + random.random() * 0.03,
                'direction': random.choice([1, -1])
            }
            for _ in range(config.MAX_LIGHTS)
        ]
        
        # Initialize spectrum colors
        palette = self._get_color_palette()
        self.spectrum_colors = [palette[i % len(palette)] for i in range(config.MAX_LIGHTS)]
        
        # Initialize psychedelic states
        self._init_psych_states()
        
        # Initialize new pattern states
        self.breathing_phases = [i * 0.3 for i in range(config.MAX_LIGHTS)]
        self.interference_phases = [(i * 0.7, i * 0.5) for i in range(config.MAX_LIGHTS)]
        
        # Initialize ripple bounce colors
        self.ripple_bounce_colors = [palette[i % len(palette)] for i in range(config.MAX_LIGHTS)]
        
        # Initialize ripple wave positions
        self.ripple_positions = [i * 0.2 for i in range(3)]  # 3 overlapping waves
        
    def set_program(self, program_name):
        """Set the current lighting program."""
        if program_name in self.PROGRAMS:
            with self.control_lock:
                self.program = program_name
                self._init_light_states()  # Reset states on program change
                
    def set_bpm_division(self, division):
        """Set BPM division (1, 2, 4, 8, or 16)."""
        with self.control_lock:
            self.bpm_division = max(1, min(16, int(division)))
            
    def set_dimming(self, value):
        """Set dimming level (0.0 to 1.0)."""
        with self.control_lock:
            self.dimming = max(0.0, min(1.0, value))
            
    def set_cool_colors(self, enabled):
        """Enable/disable cool colors only mode."""
        with self.control_lock:
            self.cool_colors_only = enabled
            self._init_light_states()  # Reset colors
            
    def _init_psych_states(self):
        """Initialize psychedelic mode states."""
        # Generate complementary color pairs
        self.psych_color_pairs = [
            ((255, 0, 0), (0, 255, 255)),      # Red/Cyan
            ((0, 0, 255), (255, 128, 0)),      # Blue/Orange
            ((0, 255, 0), (255, 0, 255)),      # Green/Magenta
            ((255, 255, 0), (128, 0, 255)),    # Yellow/Purple
            ((255, 0, 128), (0, 255, 128)),    # Pink/Teal
        ]
        
        # Random phase offsets for each light
        self.psych_phase_offsets = [random.random() * 2 * math.pi for _ in range(config.MAX_LIGHTS)]
        
        # Flicker states
        self.psych_flicker_states = [random.random() * 0.15 for _ in range(config.MAX_LIGHTS)]
    
    def _get_color_palette(self):
        """Get the appropriate color palette."""
        return self.COLORS_COOL if self.cool_colors_only else self.COLORS_FULL
    
    def _get_complementary_color(self, color):
        """Get complementary color using color wheel math."""
        r, g, b = color
        return (255 - r, 255 - g, 255 - b)
        
    def _should_trigger_effect(self):
        """Check if effect should trigger based on beat division."""
        if not self.beat_occurred:
            return False
            
        self.beat_counter += 1
        if self.beat_counter >= self.bpm_division:
            self.beat_counter = 0
            return True
        return False
        
    def _compute_dmx_frame(self):
        """Compute DMX frame based on current program."""
        data = array.array('B', [0] * config.DMX_CHANNELS)
        
        # Get current audio state
        audio_state = self.audio_analyzer.get_state()
        intensity = audio_state['intensity']
        audio_active = audio_state['audio_active']
        
        # If audio is not active, return blackout frame
        if not audio_active:
            # Debug: only print once per state change
            if not hasattr(self, '_last_audio_state') or self._last_audio_state != audio_active:
                print("SimpleDmxController: Audio inactive, sending blackout")
                self._last_audio_state = audio_active
            return data
        
        # Debug: only print once per state change  
        if not hasattr(self, '_last_audio_state') or self._last_audio_state != audio_active:
            print("SimpleDmxController: Audio active, sending light patterns")
            self._last_audio_state = audio_active
        
        # Select program method
        if self.program == "Bounce (Same Color)":
            self._program_bounce_same(data, intensity)
        elif self.program == "Bounce (Different Colors)":
            self._program_bounce_different(data, intensity)
        elif self.program == "Bounce (Discrete)":
            self._program_bounce_discrete(data, intensity)
        elif self.program == "Swell (Different Colors)":
            self._program_swell_different(data, intensity)
        elif self.program == "Swell (Same Color)":
            self._program_swell_same(data, intensity)
        elif self.program == "Disco":
            self._program_disco(data, intensity)
        elif self.program == "Psych":
            self._program_psych(data, audio_state)
        elif self.program == "Pulse":
            self._program_pulse(data, audio_state)
        elif self.program == "Spectrum":
            self._program_spectrum(data, audio_state)
        elif self.program == "Strobe":
            self._program_strobe(data, intensity)
        elif self.program == "Chase":
            self._program_chase(data, intensity)
        elif self.program == "Center Burst":
            self._program_center_burst(data, intensity)
        elif self.program == "VU Meter":
            self._program_vu_meter(data, intensity)
        elif self.program == "Ripple":
            self._program_ripple(data, intensity)
        elif self.program == "Alternating":
            self._program_alternating(data, intensity)
        elif self.program == "Kaleidoscope":
            self._program_kaleidoscope(data, audio_state)
        elif self.program == "Spiral":
            self._program_spiral(data, audio_state)
        elif self.program == "Breathing":
            self._program_breathing(data, audio_state)
        elif self.program == "Interference":
            self._program_interference(data, audio_state)
        elif self.program == "Color Ripples":
            self._program_color_ripples(data, audio_state)
        elif self.program == "Ripple Bounce":
            self._program_ripple_bounce(data, audio_state)
        elif self.program == "Ripple Bounce Color":
            self._program_ripple_bounce_color(data, audio_state)
        elif self.program == "DJ Mode":
            self._program_dj_mode(data, audio_state)
            
        return data
        
    def _program_bounce_same(self, data, intensity):
        """Bounce effect with same color wave."""
        palette = self._get_color_palette()
        
        # Update position on beat division
        if self._should_trigger_effect():
            self.bounce_position += self.bounce_direction
            
            # Check for direction change
            if self.bounce_position >= self.active_lights - 1:
                self.bounce_position = self.active_lights - 1
                self.bounce_direction = -1
                # Change color when hitting the end
                self.bounce_color_index = (self.bounce_color_index + 1) % len(palette)
            elif self.bounce_position <= 0:
                self.bounce_position = 0
                self.bounce_direction = 1
                # Change color when hitting the start
                self.bounce_color_index = (self.bounce_color_index + 1) % len(palette)
        
        current_color = palette[self.bounce_color_index]
        next_color = palette[(self.bounce_color_index + 1) % len(palette)]
        
        # Apply bounce with fade
        for i in range(self.active_lights):
            # Calculate distance from bounce position
            distance = abs(i - self.bounce_position)
            
            if distance == 0:
                # Peak position - transitioning color
                if (self.bounce_direction == 1 and i == self.active_lights - 1) or \
                   (self.bounce_direction == -1 and i == 0):
                    # At the edge, show next color
                    color = next_color
                else:
                    color = current_color
                brightness = 1.0
            elif distance == 1:
                # Adjacent positions - fading
                color = current_color
                brightness = 0.5
            elif distance == 2:
                # Further positions - dimmer
                color = current_color
                brightness = 0.2
            else:
                # Far positions - very dim
                color = current_color
                brightness = 0.05
            
            # Apply dimming control
            brightness *= self.dimming
            
            r, g, b = color
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_bounce_different(self, data, intensity):
        """Bounce effect with different colors per light."""
        palette = self._get_color_palette()
        
        # Update position on beat division
        if self._should_trigger_effect():
            self.bounce_position += self.bounce_direction
            
            # Check for direction change
            if self.bounce_position >= self.active_lights - 1:
                self.bounce_position = self.active_lights - 1
                self.bounce_direction = -1
            elif self.bounce_position <= 0:
                self.bounce_position = 0
                self.bounce_direction = 1
                
            # Update colors for the active position
            self.bounce_colors[self.bounce_position] = random.choice(palette)
        
        # Apply bounce with fade and different colors
        for i in range(self.active_lights):
            distance = abs(i - self.bounce_position)
            
            if distance == 0:
                # Peak position
                brightness = 1.0
            elif distance == 1:
                # Adjacent positions
                brightness = 0.5
            elif distance == 2:
                # Further positions
                brightness = 0.2
            else:
                # Far positions
                brightness = 0.05
            
            # Apply dimming control
            brightness *= self.dimming
            
            r, g, b = self.bounce_colors[i]
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_bounce_discrete(self, data, intensity):
        """Bounce effect without fades (strobing)."""
        palette = self._get_color_palette()
        
        # Update position on beat division
        if self._should_trigger_effect():
            self.bounce_position += self.bounce_direction
            
            # Check for direction change
            if self.bounce_position >= self.active_lights - 1:
                self.bounce_position = self.active_lights - 1
                self.bounce_direction = -1
            elif self.bounce_position <= 0:
                self.bounce_position = 0
                self.bounce_direction = 1
                
            # Update color for the active position
            self.bounce_colors[self.bounce_position] = random.choice(palette)
        
        # Apply discrete bounce (only active position is on)
        for i in range(self.active_lights):
            if i == self.bounce_position:
                r, g, b = self.bounce_colors[i]
                self._set_light_color(data, i, r, g, b, self.dimming)
            else:
                # Light is off
                self._set_light_color(data, i, 0, 0, 0, 0)
                
    def _program_swell_different(self, data, intensity):
        """All lights swell together with different colors."""
        palette = self._get_color_palette()
        
        # Update colors on beat division
        if self._should_trigger_effect():
            for i in range(self.active_lights):
                # Each light gets a different color from palette
                color_idx = (self.swell_color_index + i) % len(palette)
                self.bounce_colors[i] = palette[color_idx]
            self.swell_color_index = (self.swell_color_index + 1) % len(palette)
        
        # Calculate swell brightness (sine wave)
        # Speed based on BPM division
        swell_speed = 0.5 / max(1, self.bpm_division)
        self.swell_phase += swell_speed * (1.0 / config.UPDATE_FPS)
        
        # Sine wave for smooth swelling, never going to complete darkness
        brightness = 0.1 + 0.9 * ((math.sin(self.swell_phase * 2 * math.pi) + 1.0) / 2.0)
        brightness *= self.dimming
        
        # Apply to all lights with their different colors
        for i in range(self.active_lights):
            r, g, b = self.bounce_colors[i]
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_swell_same(self, data, intensity):
        """All lights swell together with same color."""
        palette = self._get_color_palette()
        
        # Update color on beat division
        if self._should_trigger_effect():
            self.swell_color_index = (self.swell_color_index + 1) % len(palette)
        
        current_color = palette[self.swell_color_index]
        
        # Calculate swell brightness
        swell_speed = 0.5 / max(1, self.bpm_division)
        self.swell_phase += swell_speed * (1.0 / config.UPDATE_FPS)
        
        # Sine wave for smooth swelling, never going to complete darkness
        brightness = 0.1 + 0.9 * ((math.sin(self.swell_phase * 2 * math.pi) + 1.0) / 2.0)
        brightness *= self.dimming
        
        # Apply same color to all lights
        r, g, b = current_color
        for i in range(self.active_lights):
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_disco(self, data, intensity):
        """Random fading lights with variety of colors."""
        palette = self._get_color_palette()
        
        # Update random states on beat division
        if self._should_trigger_effect():
            for state in self.disco_states:
                # Randomly change some lights
                if random.random() < 0.3:  # 30% chance to change
                    state['color'] = random.choice(palette)
                    state['direction'] = random.choice([1, -1])
                    state['fade_speed'] = 0.01 + random.random() * 0.03
        
        # Update and apply disco states
        for i in range(self.active_lights):
            state = self.disco_states[i]
            
            # Update brightness
            state['brightness'] += state['fade_speed'] * state['direction']
            
            # Reverse at limits
            if state['brightness'] >= 1.0:
                state['brightness'] = 1.0
                state['direction'] = -1
            elif state['brightness'] <= 0.0:
                state['brightness'] = 0.0
                state['direction'] = 1
                # Change color when fading back in
                state['color'] = random.choice(palette)
            
            # Apply
            r, g, b = state['color']
            brightness = state['brightness'] * self.dimming
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_psych(self, data, audio_state):
        """Enhanced psychedelic kaleidoscopic effects."""
        intensity = audio_state['intensity']
        bass = audio_state.get('bass', 0)
        mid = audio_state.get('mid', 0) 
        high = audio_state.get('high', 0)
        
        # Update pattern timer and switch patterns
        if self.beat_occurred:
            self.psych_beat_count += 1
            if self.psych_beat_count >= 16:  # Change pattern every 16 beats
                self.psych_pattern_type = (self.psych_pattern_type + 1) % 5
                self.psych_symmetry_mode = random.randint(0, 2)
                self.psych_beat_count = 0
                # Reinitialize some states for variety
                self._init_psych_states()
        
        # Update phase and morphing
        phase_speed = (0.5 + bass * 0.5) / max(1, self.bpm_division)
        self.psych_phase += phase_speed * (1.0 / config.UPDATE_FPS)
        self.psych_spiral_angle += (mid * 0.1 + 0.02) * (1.0 / config.UPDATE_FPS)
        self.psych_morph_progress += (high * 0.05 + 0.01) * (1.0 / config.UPDATE_FPS)
        
        # Get current color pair
        pair_index = int(self.psych_morph_progress) % len(self.psych_color_pairs)
        next_pair_index = (pair_index + 1) % len(self.psych_color_pairs)
        morph_t = self.psych_morph_progress - int(self.psych_morph_progress)
        
        color_pair_1 = self.psych_color_pairs[pair_index]
        color_pair_2 = self.psych_color_pairs[next_pair_index]
        
        # Apply different patterns based on current type
        for i in range(self.active_lights):
            # Calculate base pattern
            if self.psych_pattern_type == 0:  # Flowing waves
                phase = self.psych_phase + self.psych_phase_offsets[i]
                wave1 = (math.sin(phase * 2 * math.pi) + 1.0) / 2.0
                wave2 = (math.sin(phase * 3 * math.pi + self.psych_spiral_angle) + 1.0) / 2.0
                pattern_value = wave1 * 0.6 + wave2 * 0.4
                
            elif self.psych_pattern_type == 1:  # Spiral
                angle = (i / self.active_lights) * 2 * math.pi + self.psych_spiral_angle
                pattern_value = (math.sin(angle * 2) + 1.0) / 2.0
                
            elif self.psych_pattern_type == 2:  # Breathing
                phase = self.psych_phase * 2 + self.psych_phase_offsets[i]
                pattern_value = (math.sin(phase) + 1.0) / 2.0
                
            elif self.psych_pattern_type == 3:  # Interference
                phase1 = self.psych_phase + i * 0.5
                phase2 = self.psych_phase * 1.5 - i * 0.3
                wave1 = math.sin(phase1 * 2 * math.pi)
                wave2 = math.sin(phase2 * 2 * math.pi)
                pattern_value = (wave1 * wave2 + 1.0) / 2.0
                
            else:  # Kaleidoscope
                # Mirror pattern
                mirror_i = i if i < self.active_lights // 2 else self.active_lights - 1 - i
                phase = self.psych_phase + mirror_i * 0.4
                pattern_value = (math.sin(phase * 2 * math.pi) + 1.0) / 2.0
            
            # Select colors based on pattern value
            if pattern_value < 0.5:
                # Use first color from pair
                base_color = color_pair_1[0]
                t = pattern_value * 2  # Remap to 0-1
            else:
                # Use second color from pair
                base_color = color_pair_1[1]
                t = (pattern_value - 0.5) * 2  # Remap to 0-1
            
            # Morph between color pairs
            target_color = color_pair_2[0] if pattern_value < 0.5 else color_pair_2[1]
            
            r = int(base_color[0] * (1 - morph_t) + target_color[0] * morph_t)
            g = int(base_color[1] * (1 - morph_t) + target_color[1] * morph_t)
            b = int(base_color[2] * (1 - morph_t) + target_color[2] * morph_t)
            
            # Apply frequency-based color modulation
            r = min(255, int(r * (1 + bass * 0.3)))
            g = min(255, int(g * (1 + mid * 0.3)))
            b = min(255, int(b * (1 + high * 0.3)))
            
            # Calculate brightness with flicker
            base_brightness = 0.3 + pattern_value * 0.5
            flicker = 1.0 - self.psych_flicker_states[i] * (0.5 + high * 0.5)
            brightness = base_brightness * flicker * (0.7 + intensity * 0.3)
            brightness *= self.dimming
            
            # Update flicker states
            if random.random() < 0.1:  # 10% chance to change flicker
                self.psych_flicker_states[i] = random.random() * 0.15
            
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_pulse(self, data, audio_state):
        """All lights pulse with volume intensity."""
        palette = self._get_color_palette()
        intensity = audio_state['intensity']
        
        # Change color on beat division
        if self._should_trigger_effect():
            self.pulse_color_index = (self.pulse_color_index + 1) % len(palette)
        
        current_color = palette[self.pulse_color_index]
        
        # Brightness directly follows volume with minimum threshold
        brightness = 0.1 + (intensity * 0.9)  # Never completely dark
        brightness *= self.dimming
        
        # Apply to all lights
        r, g, b = current_color
        for i in range(self.active_lights):
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_spectrum(self, data, audio_state):
        """Display frequency spectrum across lights."""
        bass = audio_state.get('bass', 0)
        mid = audio_state.get('mid', 0)
        high = audio_state.get('high', 0)
        
        # Divide lights into three groups
        lights_per_band = max(1, self.active_lights // 3)
        
        # Color mapping for frequency bands
        if self.cool_colors_only:
            bass_color = (0, 255, 128)    # Teal for bass
            mid_color = (0, 255, 0)       # Green for mids
            high_color = (0, 128, 255)    # Blue for highs
        else:
            bass_color = (255, 0, 0)      # Red for bass
            mid_color = (255, 255, 0)     # Yellow for mids
            high_color = (0, 128, 255)    # Blue for highs
        
        # Apply frequency levels to light groups
        for i in range(self.active_lights):
            if i < lights_per_band:
                # Bass group (left)
                brightness = 0.1 + (bass * 0.9)
                r, g, b = bass_color
            elif i < lights_per_band * 2:
                # Mid group (center)
                brightness = 0.1 + (mid * 0.9)
                r, g, b = mid_color
            else:
                # High group (right)
                brightness = 0.1 + (high * 0.9)
                r, g, b = high_color
            
            brightness *= self.dimming
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_strobe(self, data, intensity):
        """Strobe effect synchronized to beats."""
        palette = self._get_color_palette()
        
        # Toggle strobe state on beat division
        if self._should_trigger_effect():
            self.strobe_on = not self.strobe_on
            if self.strobe_on:
                # Change color when turning on
                self.strobe_color_index = (self.strobe_color_index + 1) % len(palette)
        
        if self.strobe_on:
            # Flash on with intensity-based brightness
            brightness = 0.5 + (intensity * 0.5)
            brightness *= self.dimming
            r, g, b = palette[self.strobe_color_index]
            
            for i in range(self.active_lights):
                self._set_light_color(data, i, r, g, b, brightness)
        else:
            # All lights off
            for i in range(self.active_lights):
                self._set_light_color(data, i, 0, 0, 0, 0)
                
    def _program_chase(self, data, intensity):
        """Continuous chase effect in one direction."""
        palette = self._get_color_palette()
        
        # Move chase position continuously
        chase_speed = 0.2 / max(1, self.bpm_division)
        self.chase_position += chase_speed
        
        # Wrap around and change color
        if self.chase_position >= self.active_lights:
            self.chase_position = 0
            self.chase_color_index = (self.chase_color_index + 1) % len(palette)
        
        current_color = palette[self.chase_color_index]
        
        # Create chase with tail
        for i in range(self.active_lights):
            # Calculate distance from chase position
            distance = abs(i - self.chase_position)
            
            # Wrap-around distance
            wrap_distance = abs(i - (self.chase_position + self.active_lights))
            distance = min(distance, wrap_distance)
            
            if distance < 1:
                # Lead position
                brightness = 1.0
            elif distance < 2:
                # Tail positions
                brightness = 0.5
            elif distance < 3:
                brightness = 0.2
            else:
                brightness = 0.05
            
            brightness *= self.dimming
            r, g, b = current_color
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_center_burst(self, data, intensity):
        """Burst effect from center outward - optimized for 4 lights."""
        palette = self._get_color_palette()
        
        # Trigger burst on beat division
        if self._should_trigger_effect():
            self.burst_radius = 0
            self.burst_color_index = (self.burst_color_index + 1) % len(palette)
        
        # Expand burst radius (0 to 1 over time)
        burst_speed = 0.25 / max(1, self.bpm_division)
        self.burst_radius = min(1.0, self.burst_radius + burst_speed)
        
        current_color = palette[self.burst_color_index]
        r, g, b = current_color
        
        # For 4-light setup: lights 0,1,2,3
        # Center lights are 1 and 2 (indices 1,2)
        # Outer lights are 0 and 3 (indices 0,3)
        
        if self.active_lights == 4:
            # Phase 1: Center lights (1 and 2) fade in and burst
            if self.burst_radius < 0.5:
                # Center lights growing brighter
                center_brightness = (self.burst_radius * 2) * (0.7 + intensity * 0.3)
                outer_brightness = 0.05  # Outer lights dim
                
                # Light 0 (outer left)
                self._set_light_color(data, 0, r, g, b, outer_brightness * self.dimming)
                # Light 1 (center left)
                self._set_light_color(data, 1, r, g, b, center_brightness * self.dimming)
                # Light 2 (center right)
                self._set_light_color(data, 2, r, g, b, center_brightness * self.dimming)
                # Light 3 (outer right)
                self._set_light_color(data, 3, r, g, b, outer_brightness * self.dimming)
                
            else:
                # Phase 2: Energy transfers to outer lights
                transfer_progress = (self.burst_radius - 0.5) * 2  # 0 to 1
                
                # Center lights fading out
                center_brightness = (1.0 - transfer_progress) * (0.7 + intensity * 0.3)
                # Outer lights absorbing the burst
                outer_brightness = transfer_progress * (0.7 + intensity * 0.3)
                
                # Light 0 (outer left) - absorbing burst
                self._set_light_color(data, 0, r, g, b, outer_brightness * self.dimming)
                # Light 1 (center left) - fading
                self._set_light_color(data, 1, r, g, b, center_brightness * self.dimming)
                # Light 2 (center right) - fading
                self._set_light_color(data, 2, r, g, b, center_brightness * self.dimming)
                # Light 3 (outer right) - absorbing burst
                self._set_light_color(data, 3, r, g, b, outer_brightness * self.dimming)
                
        else:
            # For other light counts, use radial burst pattern
            center = self.active_lights / 2.0
            
            for i in range(self.active_lights):
                # Calculate distance from center
                distance_from_center = abs(i - center + 0.5) / (self.active_lights / 2.0)
                
                if self.burst_radius < 0.5:
                    # Burst expanding from center
                    if distance_from_center < 0.5:
                        # Center lights
                        brightness = (self.burst_radius * 2) * (0.7 + intensity * 0.3)
                    else:
                        # Outer lights
                        brightness = 0.05
                else:
                    # Energy transferring outward
                    transfer_progress = (self.burst_radius - 0.5) * 2
                    
                    if distance_from_center < 0.5:
                        # Center lights fading
                        brightness = (1.0 - transfer_progress) * (0.7 + intensity * 0.3)
                    else:
                        # Outer lights absorbing
                        brightness = transfer_progress * (0.7 + intensity * 0.3)
                
                brightness *= self.dimming
                self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_vu_meter(self, data, intensity):
        """Volume meter visualization."""
        # Calculate how many lights to illuminate based on volume
        lit_lights = int(intensity * self.active_lights)
        
        # Smooth peak decay
        if lit_lights > self.vu_peak:
            self.vu_peak = lit_lights
        else:
            self.vu_peak = max(0, self.vu_peak - 0.1)
        
        # Apply VU meter with color gradient
        for i in range(self.active_lights):
            if i < lit_lights:
                # Calculate color based on position (green to yellow to red)
                position_ratio = i / max(1, self.active_lights - 1)
                
                if position_ratio < 0.5:
                    # Green to yellow
                    r = int(255 * (position_ratio * 2))
                    g = 255
                    b = 0
                else:
                    # Yellow to red
                    r = 255
                    g = int(255 * (2 - position_ratio * 2))
                    b = 0
                
                brightness = 1.0 * self.dimming
            elif i == int(self.vu_peak):
                # Peak indicator
                r, g, b = 255, 255, 255
                brightness = 0.5 * self.dimming
            else:
                # Off
                r, g, b = 0, 0, 0
                brightness = 0
            
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_ripple(self, data, intensity):
        """Ripple waves flowing across lights."""
        palette = self._get_color_palette()
        
        # Update wave positions
        wave_speed = 0.1 / max(1, self.bpm_division)
        for i in range(len(self.ripple_positions)):
            self.ripple_positions[i] += wave_speed
            # Wrap around
            if self.ripple_positions[i] >= self.active_lights + 5:
                self.ripple_positions[i] = -5
        
        # Apply multiple overlapping waves
        for i in range(self.active_lights):
            brightness = 0.05  # Base brightness
            r, g, b = 0, 0, 0
            
            # Check each wave
            for wave_idx, wave_pos in enumerate(self.ripple_positions):
                distance = abs(i - wave_pos)
                
                if distance < 3:
                    # Wave affects this light
                    wave_brightness = 1.0 - (distance / 3.0)
                    wave_brightness *= 0.7  # Scale down for overlapping
                    
                    # Different color for each wave
                    wave_color = palette[(wave_idx * 3) % len(palette)]
                    
                    # Additive color mixing
                    r = min(255, r + int(wave_color[0] * wave_brightness))
                    g = min(255, g + int(wave_color[1] * wave_brightness))
                    b = min(255, b + int(wave_color[2] * wave_brightness))
                    
                    brightness = min(1.0, brightness + wave_brightness)
            
            brightness *= self.dimming
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_alternating(self, data, intensity):
        """Alternating even/odd lights pattern."""
        palette = self._get_color_palette()
        
        # Toggle state on beat division
        if self._should_trigger_effect():
            self.alternating_state = not self.alternating_state
            self.alternating_color_index = (self.alternating_color_index + 1) % len(palette)
        
        color1 = palette[self.alternating_color_index]
        color2 = palette[(self.alternating_color_index + len(palette) // 2) % len(palette)]
        
        # Apply alternating pattern
        for i in range(self.active_lights):
            is_even = (i % 2 == 0)
            
            if (is_even and self.alternating_state) or (not is_even and not self.alternating_state):
                r, g, b = color1
                brightness = 0.8
            else:
                r, g, b = color2
                brightness = 0.3
            
            # Modulate with intensity
            brightness *= (0.5 + intensity * 0.5)
            brightness *= self.dimming
            
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_kaleidoscope(self, data, audio_state):
        """Kaleidoscope mirror pattern with symmetry."""
        intensity = audio_state['intensity']
        bass = audio_state.get('bass', 0)
        
        palette = self._get_color_palette()
        
        # Rotate angle based on bass
        rotation_speed = 0.05 + bass * 0.1
        self.kaleidoscope_angle += rotation_speed / max(1, self.bpm_division)
        
        # Change color on beat
        if self._should_trigger_effect():
            self.kaleidoscope_color_index = (self.kaleidoscope_color_index + 1) % len(palette)
        
        center = self.active_lights / 2.0
        
        for i in range(self.active_lights):
            # Create mirror effect from center
            distance_from_center = abs(i - center) / center
            
            # Apply rotating wave pattern
            wave_phase = self.kaleidoscope_angle + distance_from_center * math.pi
            wave_value = (math.sin(wave_phase * 2) + 1.0) / 2.0
            
            # Interpolate between two colors
            color1 = palette[self.kaleidoscope_color_index]
            color2 = palette[(self.kaleidoscope_color_index + 1) % len(palette)]
            
            r = int(color1[0] * (1 - wave_value) + color2[0] * wave_value)
            g = int(color1[1] * (1 - wave_value) + color2[1] * wave_value)
            b = int(color1[2] * (1 - wave_value) + color2[2] * wave_value)
            
            # Brightness based on distance and intensity
            brightness = (1.0 - distance_from_center * 0.3) * (0.5 + intensity * 0.5)
            brightness *= self.dimming
            
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_spiral(self, data, audio_state):
        """Continuous spiral flow pattern."""
        intensity = audio_state['intensity']
        mid = audio_state.get('mid', 0)
        
        palette = self._get_color_palette()
        
        # Spiral movement speed based on mids
        spiral_speed = 0.1 + mid * 0.2
        self.spiral_position += spiral_speed / max(1, self.bpm_division)
        
        # Color phase shifts slower
        self.spiral_color_phase += 0.02
        
        for i in range(self.active_lights):
            # Calculate spiral position for this light
            spiral_offset = (i / self.active_lights) * 2 * math.pi
            phase = self.spiral_position * 2 * math.pi + spiral_offset
            
            # Create spiral wave
            wave = (math.sin(phase) + 1.0) / 2.0
            
            # Color selection with smooth transition
            color_pos = (self.spiral_color_phase + wave) % 1.0
            color_index = int(color_pos * len(palette))
            next_index = (color_index + 1) % len(palette)
            
            t = (color_pos * len(palette)) - color_index
            color1 = palette[color_index]
            color2 = palette[next_index]
            
            r = int(color1[0] * (1 - t) + color2[0] * t)
            g = int(color1[1] * (1 - t) + color2[1] * t)
            b = int(color1[2] * (1 - t) + color2[2] * t)
            
            brightness = 0.3 + wave * 0.5 + intensity * 0.2
            brightness *= self.dimming
            
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_breathing(self, data, audio_state):
        """Organic breathing pattern with phase offsets."""
        intensity = audio_state['intensity']
        bass = audio_state.get('bass', 0)
        
        palette = self._get_color_palette()
        
        # Breathing rate influenced by bass
        breath_rate = 0.03 + bass * 0.02
        
        for i in range(self.active_lights):
            # Update individual breathing phases
            self.breathing_phases[i] += breath_rate / max(1, self.bpm_division)
            
            # Calculate breath value (smooth sine wave)
            breath = (math.sin(self.breathing_phases[i]) + 1.0) / 2.0
            
            # Color shifts slowly through palette
            color_offset = (self.breathing_phases[i] * 0.1) % 1.0
            color_index = int(color_offset * len(palette))
            
            r, g, b = palette[color_index]
            
            # Apply complementary color on alternate lights
            if i % 2 == 1:
                r, g, b = self._get_complementary_color((r, g, b))
            
            # Breathing brightness
            brightness = 0.2 + breath * 0.6 + intensity * 0.2
            brightness *= self.dimming
            
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_interference(self, data, audio_state):
        """Wave interference patterns creating moiré effects."""
        intensity = audio_state['intensity']
        high = audio_state.get('high', 0)
        
        palette = self._get_color_palette()
        
        # Wave speeds influenced by highs
        wave1_speed = 0.05 + high * 0.05
        wave2_speed = 0.03 + high * 0.07
        
        for i in range(self.active_lights):
            # Update dual wave phases
            phase1, phase2 = self.interference_phases[i]
            phase1 += wave1_speed / max(1, self.bpm_division)
            phase2 += wave2_speed / max(1, self.bpm_division)
            self.interference_phases[i] = (phase1, phase2)
            
            # Calculate interference pattern
            wave1 = math.sin(phase1 * 2 * math.pi)
            wave2 = math.sin(phase2 * 3 * math.pi)
            
            # Interference creates complex patterns
            interference = (wave1 * wave2 + 1.0) / 2.0
            
            # Color based on interference value
            if interference < 0.33:
                color = palette[0]
            elif interference < 0.67:
                color = palette[len(palette) // 2]
            else:
                color = palette[-1]
            
            r, g, b = color
            
            # Modulate colors with interference
            r = int(r * (0.5 + interference * 0.5))
            g = int(g * (0.5 + interference * 0.5))
            b = int(b * (0.5 + interference * 0.5))
            
            brightness = 0.3 + interference * 0.4 + intensity * 0.3
            brightness *= self.dimming
            
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_color_ripples(self, data, audio_state):
        """Ripples of color emanating from beat-triggered centers."""
        intensity = audio_state['intensity']
        
        palette = self._get_color_palette()
        
        # Trigger new ripple on beat
        if self._should_trigger_effect() and len(self.color_ripple_centers) < 3:
            # Add new ripple at random position
            self.color_ripple_centers.append({
                'position': random.randint(0, self.active_lights - 1),
                'radius': 0.0,
                'color': random.choice(palette),
                'speed': 0.1 + random.random() * 0.1
            })
        
        # Update and render ripples
        for i in range(self.active_lights):
            r_total, g_total, b_total = 0, 0, 0
            brightness_total = 0
            active_ripples = 0
            
            # Process each ripple
            for ripple in self.color_ripple_centers[:]:
                ripple['radius'] += ripple['speed'] / max(1, self.bpm_division)
                
                # Remove ripple if it's too large
                if ripple['radius'] > self.active_lights:
                    self.color_ripple_centers.remove(ripple)
                    continue
                
                # Calculate distance from ripple center
                distance = abs(i - ripple['position'])
                
                # Check if this light is affected by the ripple
                if abs(distance - ripple['radius']) < 1.5:
                    # Calculate ripple intensity (bell curve)
                    ripple_intensity = math.exp(-((distance - ripple['radius']) ** 2) / 0.5)
                    
                    r, g, b = ripple['color']
                    r_total += r * ripple_intensity
                    g_total += g * ripple_intensity
                    b_total += b * ripple_intensity
                    brightness_total += ripple_intensity
                    active_ripples += 1
            
            # Average the ripple effects
            if active_ripples > 0:
                r = min(255, int(r_total / active_ripples))
                g = min(255, int(g_total / active_ripples))
                b = min(255, int(b_total / active_ripples))
                brightness = min(1.0, brightness_total / active_ripples)
            else:
                # Dim background
                r, g, b = palette[0]
                brightness = 0.1
            
            brightness *= (0.5 + intensity * 0.5) * self.dimming
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_ripple_bounce(self, data, audio_state):
        """Ripple effect that bounces back and forth, changing color on each pass."""
        intensity = audio_state['intensity']
        palette = self._get_color_palette()
        
        # Move on beat
        if self._should_trigger_effect():
            # Start new ripple pass
            if self.ripple_bounce_direction == 1 and self.ripple_bounce_position >= self.active_lights - 1:
                # Hit the end, bounce back
                self.ripple_bounce_direction = -1
                self.ripple_bounce_position = self.active_lights - 1
                # Change color on direction change
                self.ripple_bounce_color_index = (self.ripple_bounce_color_index + 1) % len(palette)
            elif self.ripple_bounce_direction == -1 and self.ripple_bounce_position <= 0:
                # Hit the start, bounce forward
                self.ripple_bounce_direction = 1
                self.ripple_bounce_position = 0
                # Change color on direction change
                self.ripple_bounce_color_index = (self.ripple_bounce_color_index + 1) % len(palette)
            else:
                # Continue in current direction
                self.ripple_bounce_position += self.ripple_bounce_direction
        
        # Smooth movement between beats
        move_speed = 0.15  # Adjust for smoothness
        self.ripple_bounce_position += self.ripple_bounce_direction * move_speed
        
        # Clamp position
        self.ripple_bounce_position = max(0, min(self.active_lights - 1, self.ripple_bounce_position))
        
        # Update trail (keep last 3 positions for tail effect)
        self.ripple_bounce_trail.append(self.ripple_bounce_position)
        if len(self.ripple_bounce_trail) > 3:
            self.ripple_bounce_trail.pop(0)
        
        current_color = palette[self.ripple_bounce_color_index]
        
        # Render the ripple with trail
        for i in range(self.active_lights):
            brightness = 0.0
            
            # Check if this light is the main position
            distance = abs(i - self.ripple_bounce_position)
            if distance < 1.0:
                # Main ripple position
                brightness = 1.0 - distance * 0.5
            
            # Check trail positions for fade effect
            for j, trail_pos in enumerate(self.ripple_bounce_trail[:-1]):  # Exclude current position
                trail_distance = abs(i - trail_pos)
                if trail_distance < 1.5:
                    # Trail brightness decreases with age
                    trail_brightness = (1.0 - trail_distance / 1.5) * (0.5 - j * 0.15)
                    brightness = max(brightness, trail_brightness)
            
            # Apply intensity modulation
            brightness *= (0.7 + intensity * 0.3)
            brightness *= self.dimming
            
            r, g, b = current_color
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_ripple_bounce_color(self, data, audio_state):
        """Ripple bounce where each light has a different color."""
        intensity = audio_state['intensity']
        palette = self._get_color_palette()
        
        # Move on beat
        if self._should_trigger_effect():
            # Start new ripple pass
            if self.ripple_bounce_direction == 1 and self.ripple_bounce_position >= self.active_lights - 1:
                # Hit the end, bounce back
                self.ripple_bounce_direction = -1
                self.ripple_bounce_position = self.active_lights - 1
                # Randomize colors for each light on direction change
                self.ripple_bounce_colors = [random.choice(palette) for _ in range(self.active_lights)]
            elif self.ripple_bounce_direction == -1 and self.ripple_bounce_position <= 0:
                # Hit the start, bounce forward
                self.ripple_bounce_direction = 1
                self.ripple_bounce_position = 0
                # Randomize colors for each light on direction change
                self.ripple_bounce_colors = [random.choice(palette) for _ in range(self.active_lights)]
            else:
                # Continue in current direction
                self.ripple_bounce_position += self.ripple_bounce_direction
        
        # Smooth movement between beats
        move_speed = 0.15  # Adjust for smoothness
        self.ripple_bounce_position += self.ripple_bounce_direction * move_speed
        
        # Clamp position
        self.ripple_bounce_position = max(0, min(self.active_lights - 1, self.ripple_bounce_position))
        
        # Update trail
        self.ripple_bounce_trail.append(self.ripple_bounce_position)
        if len(self.ripple_bounce_trail) > 3:
            self.ripple_bounce_trail.pop(0)
        
        # Render the ripple with individual colors
        for i in range(self.active_lights):
            brightness = 0.0
            
            # Check if this light is near the ripple position
            distance = abs(i - self.ripple_bounce_position)
            if distance < 1.0:
                # Main ripple position - full brightness
                brightness = 1.0 - distance * 0.5
            
            # Check trail positions for fade effect
            for j, trail_pos in enumerate(self.ripple_bounce_trail[:-1]):
                trail_distance = abs(i - trail_pos)
                if trail_distance < 1.5:
                    # Trail brightness decreases with age
                    trail_brightness = (1.0 - trail_distance / 1.5) * (0.5 - j * 0.15)
                    brightness = max(brightness, trail_brightness)
            
            # Use this light's assigned color
            r, g, b = self.ripple_bounce_colors[i % len(self.ripple_bounce_colors)]
            
            # Apply intensity modulation
            brightness *= (0.7 + intensity * 0.3)
            brightness *= self.dimming
            
            self._set_light_color(data, i, r, g, b, brightness)
            
    def _program_dj_mode(self, data, audio_state):
        """DJ Mode - Automatically switches between programs based on music characteristics."""
        intensity = audio_state['intensity']
        bass = audio_state.get('bass', 0)
        mid = audio_state.get('mid', 0)
        high = audio_state.get('high', 0)
        bpm = audio_state.get('bpm', 120)
        
        # Update running averages with smoothing
        alpha = 0.1  # Smoothing factor
        self.dj_intensity_avg = alpha * intensity + (1 - alpha) * self.dj_intensity_avg
        self.dj_bass_avg = alpha * bass + (1 - alpha) * self.dj_bass_avg
        self.dj_high_avg = alpha * high + (1 - alpha) * self.dj_high_avg
        
        # Track energy history for trend detection
        self.dj_energy_history.append(intensity)
        if len(self.dj_energy_history) > 30:  # Keep last second at 30fps
            self.dj_energy_history.pop(0)
        
        # Count beats in current program
        if self.beat_occurred:
            self.dj_program_beats += 1
        
        # Detect build-ups and drops
        if len(self.dj_energy_history) >= 30:
            recent_avg = sum(self.dj_energy_history[-10:]) / 10
            older_avg = sum(self.dj_energy_history[:10]) / 10
            
            # Build-up detection (energy increasing)
            if recent_avg > older_avg * 1.3 and self.dj_intensity_avg > 0.6:
                self.dj_build_detected = True
                self.dj_drop_countdown = 8  # Expect drop in ~8 beats
                
            # Drop detection (sudden energy spike)
            if intensity > 0.9 and self.dj_bass_avg > 0.7:
                self.dj_drop_countdown = 0
                self.dj_build_detected = False
        
        # Decide if it's time to switch programs
        should_switch = False
        new_program = self.dj_current_program
        
        if self.dj_program_beats >= self.dj_min_beats:
            # Categorize energy level and select appropriate program
            energy_level = self._categorize_energy()
            
            if self.dj_drop_countdown == 0 and self.dj_build_detected:
                # DROP! Go crazy
                program_choices = ["Center Burst", "Strobe", "Color Ripples", "Disco"]
                new_program = random.choice(program_choices)
                self.dj_min_beats = 8  # Short duration for drop
                self.dj_build_detected = False
                should_switch = True
                
            elif energy_level == "chill":
                # Low energy - ambient programs
                program_choices = ["Breathing", "Swell (Same Color)", "Spiral"]
                # Add some variety based on frequency content
                if self.dj_high_avg > 0.5:
                    program_choices.append("Kaleidoscope")
                new_program = random.choice([p for p in program_choices if p != self.dj_current_program])
                self.dj_min_beats = 24  # Longer duration for chill
                should_switch = True
                
            elif energy_level == "groovy":
                # Medium energy - rhythmic programs
                program_choices = ["Bounce (Same Color)", "Bounce (Different Colors)", 
                                 "Ripple", "Ripple Bounce", "Chase", "Alternating"]
                # Prefer bounce programs for steady beats
                if bpm > 100 and bpm < 130:
                    program_choices.extend(["Bounce (Same Color)", "Ripple Bounce"])
                new_program = random.choice([p for p in program_choices if p != self.dj_current_program])
                self.dj_min_beats = 16  # Medium duration
                should_switch = True
                
            elif energy_level == "energetic":
                # High energy - dynamic programs
                program_choices = ["Disco", "Pulse", "Bounce (Discrete)", 
                                 "Ripple Bounce Color", "Chase", "Alternating"]
                # Add psychedelic elements if high frequencies are prominent
                if self.dj_high_avg > 0.6:
                    program_choices.extend(["Psych", "Interference"])
                new_program = random.choice([p for p in program_choices if p != self.dj_current_program])
                self.dj_min_beats = 12  # Shorter duration for energy
                should_switch = True
                
            elif energy_level == "peak":
                # Maximum energy - intense programs
                program_choices = ["Strobe", "Center Burst", "Color Ripples", "Psych", 
                                 "Kaleidoscope", "Interference"]
                # Bass-heavy? Add pulse
                if self.dj_bass_avg > 0.7:
                    program_choices.append("Pulse")
                new_program = random.choice([p for p in program_choices if p != self.dj_current_program])
                self.dj_min_beats = 8  # Short bursts at peak
                should_switch = True
        
        # Handle build-up countdown
        if self.dj_drop_countdown > 0:
            self.dj_drop_countdown -= 1
            # During build-up, use programs that create tension
            if self.dj_drop_countdown < 4 and self.dj_current_program not in ["Swell (Different Colors)", "Pulse"]:
                new_program = "Swell (Different Colors)"  # Building tension
                should_switch = True
                self.dj_min_beats = 4
        
        # Switch program if needed
        if should_switch and new_program != self.dj_current_program:
            self.dj_current_program = new_program
            self.dj_program_beats = 0
            self.dj_last_switch_time = time.time()
            
            # Reset some states for smooth transition
            self.bounce_position = 0
            self.bounce_direction = 1
            self.chase_position = 0
            self.ripple_bounce_position = 0
            self.ripple_bounce_direction = 1
            self.burst_radius = 0
            self.swell_phase = 0.0
        
        # Now run the selected program
        temp_program = self.program  # Save original
        self.program = self.dj_current_program  # Temporarily set
        
        # Call the appropriate program based on what's selected
        if self.dj_current_program == "Bounce (Same Color)":
            self._program_bounce_same(data, intensity)
        elif self.dj_current_program == "Bounce (Different Colors)":
            self._program_bounce_different(data, intensity)
        elif self.dj_current_program == "Bounce (Discrete)":
            self._program_bounce_discrete(data, intensity)
        elif self.dj_current_program == "Swell (Different Colors)":
            self._program_swell_different(data, intensity)
        elif self.dj_current_program == "Swell (Same Color)":
            self._program_swell_same(data, intensity)
        elif self.dj_current_program == "Disco":
            self._program_disco(data, intensity)
        elif self.dj_current_program == "Psych":
            self._program_psych(data, audio_state)
        elif self.dj_current_program == "Pulse":
            self._program_pulse(data, audio_state)
        elif self.dj_current_program == "Spectrum":
            self._program_spectrum(data, audio_state)
        elif self.dj_current_program == "Strobe":
            self._program_strobe(data, intensity)
        elif self.dj_current_program == "Chase":
            self._program_chase(data, intensity)
        elif self.dj_current_program == "Center Burst":
            self._program_center_burst(data, intensity)
        elif self.dj_current_program == "VU Meter":
            self._program_vu_meter(data, intensity)
        elif self.dj_current_program == "Ripple":
            self._program_ripple(data, intensity)
        elif self.dj_current_program == "Alternating":
            self._program_alternating(data, intensity)
        elif self.dj_current_program == "Kaleidoscope":
            self._program_kaleidoscope(data, audio_state)
        elif self.dj_current_program == "Spiral":
            self._program_spiral(data, audio_state)
        elif self.dj_current_program == "Breathing":
            self._program_breathing(data, audio_state)
        elif self.dj_current_program == "Interference":
            self._program_interference(data, audio_state)
        elif self.dj_current_program == "Color Ripples":
            self._program_color_ripples(data, audio_state)
        elif self.dj_current_program == "Ripple Bounce":
            self._program_ripple_bounce(data, audio_state)
        elif self.dj_current_program == "Ripple Bounce Color":
            self._program_ripple_bounce_color(data, audio_state)
        
        self.program = temp_program  # Restore original
        
    def _categorize_energy(self):
        """Categorize the current energy level of the music."""
        # Combined score based on intensity, bass, and highs
        energy_score = (self.dj_intensity_avg * 0.5 + 
                       self.dj_bass_avg * 0.3 + 
                       self.dj_high_avg * 0.2)
        
        if energy_score < 0.25:
            return "chill"
        elif energy_score < 0.45:
            return "groovy"
        elif energy_score < 0.65:
            return "energetic"
        else:
            return "peak"