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
                'brightness': random.random(),
                'fade_speed': 0.01 + random.random() * 0.03,
                'direction': random.choice([1, -1])
            }
            for _ in range(config.MAX_LIGHTS)
        ]
        
        # Initialize spectrum colors
        palette = self._get_color_palette()
        self.spectrum_colors = [palette[i % len(palette)] for i in range(config.MAX_LIGHTS)]
        
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
            
    def _get_color_palette(self):
        """Get the appropriate color palette."""
        return self.COLORS_COOL if self.cool_colors_only else self.COLORS_FULL
        
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
            self._program_psych(data, intensity)
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
            
    def _program_psych(self, data, intensity):
        """Psychedelic smooth effects with creative patterns."""
        palette = self._get_color_palette()
        
        # Update phase based on beat division
        phase_speed = 0.3 / max(1, self.bpm_division)
        self.psych_phase += phase_speed * (1.0 / config.UPDATE_FPS)
        
        # Create multiple overlapping waves for psychedelic effect
        for i in range(self.active_lights):
            # Each light has different phase offset for flowing effect
            light_phase = self.psych_phase + (i * 0.3)
            
            # Multiple sine waves at different frequencies
            wave1 = (math.sin(light_phase * 2 * math.pi) + 1.0) / 2.0
            wave2 = (math.sin(light_phase * 3 * math.pi) + 1.0) / 2.0
            wave3 = (math.sin(light_phase * 1.5 * math.pi) + 1.0) / 2.0
            
            # Blend waves for complex pattern
            blend = (wave1 * 0.5 + wave2 * 0.3 + wave3 * 0.2)
            
            # Color morphing based on waves
            color_index = int(blend * len(palette)) % len(palette)
            next_index = (color_index + 1) % len(palette)
            
            # Interpolate between colors
            color1 = palette[color_index]
            color2 = palette[next_index]
            
            # Smooth color blending
            t = blend - int(blend)
            r = int(color1[0] * (1 - t) + color2[0] * t)
            g = int(color1[1] * (1 - t) + color2[1] * t)
            b = int(color1[2] * (1 - t) + color2[2] * t)
            
            # Brightness varies smoothly
            brightness = 0.3 + 0.7 * wave1  # Never too dark
            brightness *= self.dimming
            
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
        """Burst effect from center outward."""
        palette = self._get_color_palette()
        
        # Trigger burst on beat division
        if self._should_trigger_effect():
            self.burst_radius = 0
            self.burst_color_index = (self.burst_color_index + 1) % len(palette)
        
        # Expand burst radius
        burst_speed = 0.15 / max(1, self.bpm_division)
        self.burst_radius += burst_speed
        
        # Reset when burst completes
        max_radius = self.active_lights / 2
        if self.burst_radius > max_radius:
            self.burst_radius = max_radius
        
        current_color = palette[self.burst_color_index]
        center = self.active_lights / 2
        
        # Apply burst effect
        for i in range(self.active_lights):
            distance = abs(i - center)
            
            if distance <= self.burst_radius:
                # Inside burst radius
                fade = 1.0 - (distance / max(1, max_radius))
                brightness = fade * (0.5 + intensity * 0.5)
            else:
                brightness = 0.05
            
            brightness *= self.dimming
            r, g, b = current_color
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