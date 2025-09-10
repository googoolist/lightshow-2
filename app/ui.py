"""
Tkinter GUI module for displaying status and controls.
"""

import tkinter as tk
from tkinter import ttk
import threading
import config


class AudioReactiveLightingGUI:
    def __init__(self, audio_analyzer, dmx_controller, stop_event):
        """
        Initialize the GUI.
        
        Args:
            audio_analyzer: Reference to audio analyzer for state access
            dmx_controller: Reference to DMX controller for mode changes
            stop_event: Threading event to signal shutdown
        """
        self.audio_analyzer = audio_analyzer
        self.dmx_controller = dmx_controller
        self.stop_event = stop_event
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Audio-Reactive DMX Controller")
        
        # Set window size
        if config.FULLSCREEN:
            self.root.attributes('-fullscreen', True)
            # Bind multiple keys to exit for safety
            self.root.bind('<Escape>', lambda e: self._on_quit())
            self.root.bind('<q>', lambda e: self._on_quit())
            self.root.bind('<Q>', lambda e: self._on_quit())
            # Allow Alt+Tab to work
            self.root.attributes('-topmost', False)
            # Don't grab exclusive focus
            self.root.focus_set()
            # Cursor is visible by default
        else:
            self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        
        # Configure window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Create UI elements
        self._create_widgets()
        
        # Initialize DMX controller with UI default values
        self._initialize_controller()
        
        # Start periodic updates
        self._schedule_update()
    
    def _create_widgets(self):
        """Create all GUI widgets - ultra-compact design for 320x480 screen."""
        # Main container with minimal padding
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top status bar (very compact)
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Audio indicator
        self.status_indicator = tk.Canvas(status_frame, width=15, height=15)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 5))
        self.status_circle = self.status_indicator.create_oval(
            2, 2, 13, 13, fill='gray', outline='black'
        )
        
        # Status text
        self.status_text = ttk.Label(status_frame, text="No Audio", font=('Arial', 9))
        self.status_text.pack(side=tk.LEFT, padx=(0, 10))
        
        # BPM
        ttk.Label(status_frame, text="BPM:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        self.bpm_label = ttk.Label(status_frame, text="0", font=('Arial', 9))
        self.bpm_label.pack(side=tk.LEFT, padx=(3, 10))
        
        # Level
        ttk.Label(status_frame, text="Level:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        self.intensity_label = ttk.Label(status_frame, text="0%", font=('Arial', 9))
        self.intensity_label.pack(side=tk.LEFT, padx=(3, 0))
        
        # Quit button (right side)
        self.quit_button = ttk.Button(
            status_frame,
            text="X",
            command=self._on_quit,
            width=3
        )
        self.quit_button.pack(side=tk.RIGHT)
        
        # Create two-column layout for sliders
        controls_container = ttk.Frame(main_frame)
        controls_container.pack(fill=tk.BOTH, expand=True)
        
        # Left column
        left_col = ttk.Frame(controls_container)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 3))
        
        # Right column
        right_col = ttk.Frame(controls_container)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(3, 0))
        
        # Speed control (left column) - default to midpoint
        self._create_slider_control(
            left_col, "Speed", 
            self._on_smoothness_change,
            0.5, "Slow", "Fast"  # Midpoint default
        )
        
        # Rainbow control (left column) - default to midpoint
        self._create_slider_control(
            left_col, "Rainbow",
            self._on_rainbow_change,
            0.5, "Single", "Full"  # Midpoint default
        )
        
        # Brightness control (left column) - default to midpoint
        self._create_slider_control(
            left_col, "Brightness",
            self._on_brightness_change,
            0.5, "Dim", "Bright"  # Midpoint default
        )
        
        # Strobe control (right column)
        self._create_slider_control(
            right_col, "Strobe",
            self._on_strobe_change,
            0.0, "Off", "Max"
        )
        
        # Pattern selector (right column)
        pattern_frame = ttk.Frame(right_col)
        pattern_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(pattern_frame, text="Pattern:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        self.pattern_var = tk.StringVar(value="Sync")  # Default to Sync pattern
        self.pattern_combo = ttk.Combobox(
            pattern_frame,
            textvariable=self.pattern_var,
            values=["Sync", "Wave", "Center", "Alternate", "Mirror"],
            state="readonly",
            width=12,
            font=('Arial', 9)
        )
        self.pattern_combo.pack(fill=tk.X, pady=(2, 0))
        self.pattern_combo.bind("<<ComboboxSelected>>", self._on_pattern_change)
        
        # Light count control (right column)
        lights_frame = ttk.Frame(right_col)
        lights_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(lights_frame, text="Lights:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        # Light count spinner frame
        spinner_frame = ttk.Frame(lights_frame)
        spinner_frame.pack(fill=tk.X, pady=(2, 0))
        
        self.light_count_var = tk.IntVar(value=config.DEFAULT_LIGHT_COUNT)
        
        # Decrement button
        ttk.Button(
            spinner_frame,
            text="-",
            width=3,
            command=self._decrement_lights
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Light count display
        self.light_count_label = ttk.Label(
            spinner_frame,
            text=str(config.DEFAULT_LIGHT_COUNT),
            font=('Arial', 10, 'bold'),
            width=3
        )
        self.light_count_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Increment button  
        ttk.Button(
            spinner_frame,
            text="+",
            width=3,
            command=self._increment_lights
        ).pack(side=tk.LEFT)
        
        # Range label
        ttk.Label(
            spinner_frame,
            text=f"(1-{config.MAX_LIGHTS})",
            font=('Arial', 8),
            foreground='gray'
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Info label at bottom
        self.info_label = ttk.Label(
            main_frame,
            text=f"{config.DEFAULT_LIGHT_COUNT} PAR • DMX 1",
            font=('Arial', 8),
            foreground='gray'
        )
        self.info_label.pack(side=tk.BOTTOM, pady=(2, 0))
    
    def _create_slider_control(self, parent, label, command, initial_value, left_label, right_label):
        """Create a compact slider control with labels."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 8))
        
        # Title
        ttk.Label(frame, text=f"{label}:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        # Slider frame
        slider_frame = ttk.Frame(frame)
        slider_frame.pack(fill=tk.X, pady=(2, 0))
        
        # Create variable based on label
        if label == "Speed":
            self.smoothness_var = tk.DoubleVar(value=initial_value)
            var = self.smoothness_var
        elif label == "Rainbow":
            self.rainbow_var = tk.DoubleVar(value=initial_value)
            var = self.rainbow_var
        elif label == "Brightness":
            self.brightness_var = tk.DoubleVar(value=initial_value)
            var = self.brightness_var
        elif label == "Strobe":
            self.strobe_var = tk.DoubleVar(value=initial_value)
            var = self.strobe_var
        else:
            var = tk.DoubleVar(value=initial_value)
        
        # Left label
        ttk.Label(slider_frame, text=left_label, font=('Arial', 8), foreground='gray').pack(side=tk.LEFT)
        
        # Slider
        slider = ttk.Scale(
            slider_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=var,
            command=command,
            length=120
        )
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        
        # Right label
        ttk.Label(slider_frame, text=right_label, font=('Arial', 8), foreground='gray').pack(side=tk.LEFT)
    
    def _initialize_controller(self):
        """Initialize the DMX controller with the UI's default values."""
        if self.dmx_controller:
            # Set initial values from sliders
            self._on_smoothness_change(self.smoothness_var.get())
            self._on_rainbow_change(self.rainbow_var.get())
            self._on_brightness_change(self.brightness_var.get())
            self._on_strobe_change(self.strobe_var.get())
            self._on_pattern_change()
            # Don't set light count on startup - controller already has default
    
    def _schedule_update(self):
        """Schedule periodic GUI updates."""
        self._update_display()
        if not self.stop_event.is_set():
            self.root.after(config.GUI_UPDATE_INTERVAL, self._schedule_update)
    
    def _update_display(self):
        """Update GUI elements with current audio state."""
        # Get current state from audio analyzer
        state = self.audio_analyzer.get_state()
        bpm = state['bpm']
        intensity = state['intensity']
        audio_active = state['audio_active']
        
        # Update BPM display (no decimal for compact view)
        self.bpm_label.config(text=f"{int(bpm)}")
        
        # Update intensity display
        intensity_percent = int(intensity * 100)
        self.intensity_label.config(text=f"{intensity_percent}%")
        
        # Update audio status indicator
        if audio_active:
            self.status_indicator.itemconfig(self.status_circle, fill='green')
            self.status_text.config(text="Playing")
        else:
            self.status_indicator.itemconfig(self.status_circle, fill='gray')
            self.status_text.config(text="No Audio")
    
    def _on_smoothness_change(self, value):
        """Handle speed slider change (inverted for smoothness)."""
        # Invert the speed value to get smoothness (0=fast/no smooth, 1=slow/smooth)
        speed = float(value)
        smoothness = 1.0 - speed  # Invert: high speed = low smoothness
        if self.dmx_controller:
            self.dmx_controller.set_smoothness(smoothness)
    
    def _on_rainbow_change(self, value):
        """Handle rainbow slider change."""
        rainbow_level = float(value)
        if self.dmx_controller:
            self.dmx_controller.set_rainbow_level(rainbow_level)
    
    def _on_brightness_change(self, value):
        """Handle brightness slider change."""
        brightness = float(value)
        if self.dmx_controller:
            self.dmx_controller.set_brightness(brightness)
    
    def _on_strobe_change(self, value):
        """Handle strobe slider change."""
        strobe_level = float(value)
        if self.dmx_controller:
            self.dmx_controller.set_strobe_level(strobe_level)
    
    def _on_pattern_change(self, event=None):
        """Handle pattern selection change."""
        pattern = self.pattern_var.get().lower()
        if self.dmx_controller:
            self.dmx_controller.set_pattern(pattern)
    
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
        self.info_label.config(text=f"{count} PAR • DMX 1")
        
        if self.dmx_controller:
            self.dmx_controller.set_light_count(count)
    
    def _on_quit(self):
        """Handle quit button click."""
        self.stop_event.set()
        self.root.after(500, self.root.destroy)
    
    def _on_closing(self):
        """Handle window close event."""
        self.stop_event.set()
        self.root.destroy()
    
    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()