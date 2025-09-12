"""
Simple mode UI with minimal controls for preset programs.
"""

import tkinter as tk
from tkinter import ttk
import config


class SimpleUI:
    """Simple mode UI with program selector and minimal controls."""
    
    def __init__(self, parent_frame, audio_analyzer, dmx_controller, stop_event):
        """
        Initialize the simple UI.
        
        Args:
            parent_frame: Parent tkinter frame to add UI elements to
            audio_analyzer: Reference to audio analyzer for state access
            dmx_controller: Reference to simple DMX controller
            stop_event: Threading event to signal shutdown
        """
        self.parent = parent_frame
        self.audio_analyzer = audio_analyzer
        self.dmx_controller = dmx_controller
        self.stop_event = stop_event
        
        # Create UI elements
        self._create_widgets()
        
        # Start periodic updates
        self._schedule_update()
        
    def _create_widgets(self):
        """Create simple UI widgets."""
        # Main container with minimal padding
        main_frame = ttk.Frame(self.parent, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar in the mode selector space - compact
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Audio indicator (small colored circle)
        self.status_indicator = tk.Canvas(status_frame, width=10, height=10)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 3))
        self.status_circle = self.status_indicator.create_oval(
            1, 1, 9, 9, fill='gray', outline='black'
        )
        
        # Audio status
        self.audio_status = ttk.Label(
            status_frame,
            text="No Audio",
            font=('Arial', 9)
        )
        self.audio_status.pack(side=tk.LEFT, padx=(0, 10))
        
        # BPM display
        ttk.Label(status_frame, text="BPM:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        self.bpm_label = ttk.Label(
            status_frame,
            text="--",
            font=('Arial', 9, 'bold'),
            foreground='blue'
        )
        self.bpm_label.pack(side=tk.LEFT, padx=(2, 10))
        
        # Level display
        ttk.Label(status_frame, text="Level:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        self.intensity_label = ttk.Label(
            status_frame,
            text="0%",
            font=('Arial', 9, 'bold'),
            foreground='green'
        )
        self.intensity_label.pack(side=tk.LEFT, padx=(2, 0))
        
        # Two-column layout for program and controls
        columns_frame = ttk.Frame(main_frame)
        columns_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Left column - Program selector
        left_col = ttk.Frame(columns_frame)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 3))
        
        program_frame = ttk.LabelFrame(left_col, text="Program", padding="5")
        program_frame.pack(fill=tk.BOTH, expand=True)
        
        self.program_var = tk.StringVar(value="Bounce (Same Color)")
        self.program_combo = ttk.Combobox(
            program_frame,
            textvariable=self.program_var,
            values=[
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
                "DJ Mode"
            ],
            state="readonly",
            font=('Arial', 9),
            width=18
        )
        self.program_combo.pack(fill=tk.X)
        self.program_combo.bind("<<ComboboxSelected>>", self._on_program_change)
        
        # Right column - BPM Sync
        right_col = ttk.Frame(columns_frame)
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(3, 0))
        
        bpm_frame = ttk.LabelFrame(right_col, text="BPM Sync", padding="5")
        bpm_frame.pack(fill=tk.BOTH, expand=True)
        
        self.bpm_sync_var = tk.StringVar(value="Every beat")
        self.bpm_sync_combo = ttk.Combobox(
            bpm_frame,
            textvariable=self.bpm_sync_var,
            values=["Every beat", "Every 2 beats", "Every 4 beats", "Every 8 beats", "Every 16 beats"],
            state="readonly",
            width=13,
            font=('Arial', 9)
        )
        self.bpm_sync_combo.pack(fill=tk.X)
        self.bpm_sync_combo.bind("<<ComboboxSelected>>", self._on_bpm_sync_change)
        
        # Dimming control - below the columns
        dim_frame = ttk.LabelFrame(main_frame, text="Dimming", padding="5")
        dim_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Dimming slider with percentage display
        slider_frame = ttk.Frame(dim_frame)
        slider_frame.pack(fill=tk.X)
        
        self.dimming_var = tk.DoubleVar(value=100.0)  # Default 100%
        
        ttk.Label(slider_frame, text="0%", font=('Arial', 8)).pack(side=tk.LEFT)
        
        self.dimming_scale = ttk.Scale(
            slider_frame,
            from_=0.0,
            to=100.0,
            orient=tk.HORIZONTAL,
            variable=self.dimming_var,
            command=self._on_dimming_change
        )
        self.dimming_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 3))
        
        ttk.Label(slider_frame, text="100%", font=('Arial', 8)).pack(side=tk.LEFT)
        
        # Dimming percentage label
        self.dimming_label = ttk.Label(slider_frame, text="(100%)", font=('Arial', 8))
        self.dimming_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Cool Colors checkbox
        self.cool_colors_var = tk.BooleanVar(value=False)
        self.cool_colors_check = ttk.Checkbutton(
            main_frame,
            text="Cool Colors Only",
            variable=self.cool_colors_var,
            command=self._on_cool_colors_toggle
        )
        self.cool_colors_check.pack(anchor=tk.W, pady=(3, 5))
        
        # Light count control
        lights_frame = ttk.LabelFrame(main_frame, text="Lights", padding="5")
        lights_frame.pack(fill=tk.X)
        
        # Light count controls in a horizontal layout
        lights_control = ttk.Frame(lights_frame)
        lights_control.pack(fill=tk.X)
        
        ttk.Label(lights_control, text="Active:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        
        # Decrement button
        ttk.Button(
            lights_control,
            text="-",
            width=3,
            command=self._decrement_lights
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Light count display
        self.light_count_var = tk.IntVar(value=config.DEFAULT_LIGHT_COUNT)
        self.light_count_label = ttk.Label(
            lights_control,
            text=str(config.DEFAULT_LIGHT_COUNT),
            font=('Arial', 10, 'bold'),
            width=2
        )
        self.light_count_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Increment button
        ttk.Button(
            lights_control,
            text="+",
            width=3,
            command=self._increment_lights
        ).pack(side=tk.LEFT)
        
        # Range label
        ttk.Label(
            lights_control,
            text=f"(1-{config.MAX_LIGHTS})",
            font=('Arial', 8),
            foreground='gray'
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        
        
    def _on_program_change(self, event=None):
        """Handle program selection change."""
        program = self.program_var.get()
        if self.dmx_controller:
            self.dmx_controller.set_program(program)
            
    def _on_bpm_sync_change(self, event=None):
        """Handle BPM sync dropdown change."""
        selection = self.bpm_sync_var.get()
        # Map selection to division value
        division_map = {
            "Every beat": 1,
            "Every 2 beats": 2,
            "Every 4 beats": 4,
            "Every 8 beats": 8,
            "Every 16 beats": 16
        }
        division = division_map.get(selection, 1)
        
        if self.dmx_controller:
            self.dmx_controller.set_bpm_division(division)
        
    def _on_dimming_change(self, value):
        """Handle dimming slider change."""
        percent = float(value)
        self.dimming_label.config(text=f"({int(percent)}%)")
        
        if self.dmx_controller:
            # Convert percentage to 0.0-1.0
            self.dmx_controller.set_dimming(percent / 100.0)
            
    def _on_cool_colors_toggle(self):
        """Handle cool colors checkbox toggle."""
        enabled = self.cool_colors_var.get()
        if self.dmx_controller:
            self.dmx_controller.set_cool_colors(enabled)
            
    def _schedule_update(self):
        """Schedule periodic display updates."""
        self._update_display()
        if not self.stop_event.is_set():
            self.parent.after(250, self._schedule_update)  # Update every 250ms
            
    def _update_display(self):
        """Update status display with current audio state."""
        if self.audio_analyzer:
            state = self.audio_analyzer.get_state()
            
            # Audio status indicator and text
            if state['audio_active']:
                self.status_indicator.itemconfig(self.status_circle, fill='green')
                self.audio_status.config(text="Playing")
            else:
                self.status_indicator.itemconfig(self.status_circle, fill='gray')
                self.audio_status.config(text="No Audio")
                
            # BPM
            bpm = state['bpm']
            if bpm > 0:
                self.bpm_label.config(text=f"{int(bpm)}")
            else:
                self.bpm_label.config(text="--")
                
            # Level/Intensity
            intensity_percent = int(state['intensity'] * 100)
            self.intensity_label.config(text=f"{intensity_percent}%")
    
    def _increment_lights(self):
        """Increment the number of active lights."""
        current = self.light_count_var.get()
        if current < config.MAX_LIGHTS:
            new_count = current + 1
            self._update_light_count(new_count)
    
    def _decrement_lights(self):
        """Decrement the number of active lights."""
        current = self.light_count_var.get()
        if current > 1:
            new_count = current - 1
            self._update_light_count(new_count)
    
    def _update_light_count(self, count):
        """Update the light count and notify controller."""
        self.light_count_var.set(count)
        self.light_count_label.config(text=str(count))
        
        if self.dmx_controller:
            self.dmx_controller.set_light_count(count)
                
    def destroy(self):
        """Clean up the UI."""
        # Nothing special needed for simple UI
        pass