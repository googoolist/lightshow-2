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
        self.root.title("Lightshow")
        
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
        """Create all GUI widgets with tabbed interface for 320x480 screen."""
        # Main container with minimal padding
        main_frame = ttk.Frame(self.root, padding="3")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top status bar (very compact)
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 3))
        
        # Audio indicator
        self.status_indicator = tk.Canvas(status_frame, width=12, height=12)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 3))
        self.status_circle = self.status_indicator.create_oval(
            2, 2, 10, 10, fill='gray', outline='black'
        )
        
        # Status text (smaller font)
        self.status_text = ttk.Label(status_frame, text="No Audio", font=('Arial', 8))
        self.status_text.pack(side=tk.LEFT, padx=(0, 8))
        
        # BPM
        ttk.Label(status_frame, text="BPM:", font=('Arial', 8, 'bold')).pack(side=tk.LEFT)
        self.bpm_label = ttk.Label(status_frame, text="0", font=('Arial', 8))
        self.bpm_label.pack(side=tk.LEFT, padx=(2, 8))
        
        # Level
        ttk.Label(status_frame, text="Level:", font=('Arial', 8, 'bold')).pack(side=tk.LEFT)
        self.intensity_label = ttk.Label(status_frame, text="0%", font=('Arial', 8))
        self.intensity_label.pack(side=tk.LEFT, padx=(2, 0))
        
        # Quit button (right side)
        self.quit_button = ttk.Button(
            status_frame,
            text="X",
            command=self._on_quit,
            width=2
        )
        self.quit_button.pack(side=tk.RIGHT)
        
        # Reset button (next to quit)
        self.reset_button = ttk.Button(
            status_frame,
            text="Reset",
            command=self._on_reset,
            width=5
        )
        self.reset_button.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self._create_main_tab()
        self._create_effects_tab()
        self._create_advanced_tab()
        
        
        # Info label at bottom
        self.info_label = ttk.Label(
            main_frame,
            text=f"{config.DEFAULT_LIGHT_COUNT} PAR • DMX 1",
            font=('Arial', 8),
            foreground='gray'
        )
        self.info_label.pack(side=tk.BOTTOM, pady=(2, 0))
    
    def _create_main_tab(self):
        """Create the main controls tab."""
        main_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text="Main")
        
        # Create two-column layout
        controls_container = ttk.Frame(main_tab, padding="5")
        controls_container.pack(fill=tk.BOTH, expand=True)
        
        # Left column
        left_col = ttk.Frame(controls_container)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 3))
        
        # Right column
        right_col = ttk.Frame(controls_container)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(3, 0))
        
        # Speed control (left column) - balanced default
        self._create_slider_control(
            left_col, "Speed", 
            self._on_smoothness_change,
            0.5, "Slow", "Fast"  # 0.5 = 50% smoothness (inverted)
        )
        
        # Rainbow control (left column) - more diversity
        self._create_slider_control(
            left_col, "Rainbow",
            self._on_rainbow_change,
            0.5, "Single", "Full"  # 0.5 = 50% rainbow
        )
        
        # Brightness control (left column)
        self._create_slider_control(
            left_col, "Brightness",
            self._on_brightness_change,
            0.5, "Dim", "Bright"
        )
        
        # Strobe control (right column)
        self._create_slider_control(
            right_col, "Strobe",
            self._on_strobe_change,
            0.0, "Off", "Max"
        )
        
        # Beat Sensitivity control (right column) - default to balanced
        self._create_slider_control(
            right_col, "Beat Sens",
            self._on_beat_sensitivity_change,
            0.5, "Subtle", "Intense"  # 0.5 = 50% sensitivity
        )
        
        # BPM Sync control (left column) - tempo percentage
        self._create_slider_control(
            left_col, "BPM Sync",
            self._on_bpm_sync_change,
            1.0, "25%", "200%"  # 1.0 = 100% of detected BPM
        )
        
        # Pattern selector
        pattern_frame = ttk.Frame(right_col)
        pattern_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(pattern_frame, text="Pattern:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        self.pattern_var = tk.StringVar(value="Wave")  # Default to wave for motion
        self.pattern_combo = ttk.Combobox(
            pattern_frame,
            textvariable=self.pattern_var,
            values=["Sync", "Wave", "Center", "Alternate", "Mirror", "Swell"],
            state="readonly",
            width=12,
            font=('Arial', 9)
        )
        self.pattern_combo.pack(fill=tk.X, pady=(2, 0))
        self.pattern_combo.bind("<<ComboboxSelected>>", self._on_pattern_change)
        
        # Light count control
        lights_frame = ttk.Frame(left_col)
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
    
    def _create_effects_tab(self):
        """Create the effects and modes tab."""
        effects_tab = ttk.Frame(self.notebook)
        self.notebook.add(effects_tab, text="Effects")
        
        # Create two-column layout
        controls_container = ttk.Frame(effects_tab, padding="5")
        controls_container.pack(fill=tk.BOTH, expand=True)
        
        # Left column
        left_col = ttk.Frame(controls_container)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 3))
        
        # Right column
        right_col = ttk.Frame(controls_container)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(3, 0))
        
        # Chaos Level slider (left column)
        self._create_slider_control(
            left_col, "Chaos",
            self._on_chaos_change,
            0.0, "None", "Wild"
        )
        
        # Echo Length slider (left column)
        self._create_slider_control(
            left_col, "Echo",
            self._on_echo_length_change,
            0.0, "Off", "Long"
        )
        
        # Color Theme dropdown (left column)
        theme_frame = ttk.Frame(left_col)
        theme_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(theme_frame, text="Theme:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        self.theme_var = tk.StringVar(value="Default")
        self.theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=["Default", "Sunset", "Ocean", "Fire", "Forest", "Galaxy", "Mono", "Warm", "Cool"],
            state="readonly",
            width=12,
            font=('Arial', 9)
        )
        self.theme_combo.pack(fill=tk.X, pady=(2, 0))
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_change)
        
        # Effect Mode dropdown (right column)
        effect_frame = ttk.Frame(right_col)
        effect_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(effect_frame, text="Effect:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        self.effect_var = tk.StringVar(value="None")
        self.effect_combo = ttk.Combobox(
            effect_frame,
            textvariable=self.effect_var,
            values=["None", "Breathe", "Sparkle", "Chase", "Pulse", "Sweep", "Firefly"],
            state="readonly",
            width=12,
            font=('Arial', 9)
        )
        self.effect_combo.pack(fill=tk.X, pady=(2, 0))
        self.effect_combo.bind("<<ComboboxSelected>>", self._on_effect_change)
        
        # Mode toggles
        modes_frame = ttk.LabelFrame(right_col, text="Modes", padding="5")
        modes_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Checkboxes in 2x2 grid
        row1 = ttk.Frame(modes_frame)
        row1.pack(fill=tk.X)
        
        self.mood_match_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row1,
            text="Mood Match",
            variable=self.mood_match_var,
            command=self._on_mood_match_toggle
        ).pack(side=tk.LEFT)
        
        self.frequency_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row1,
            text="Frequency",
            variable=self.frequency_var,
            command=self._on_frequency_toggle
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        row2 = ttk.Frame(modes_frame)
        row2.pack(fill=tk.X, pady=(4, 0))
        
        self.ambient_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row2,
            text="Ambient",
            variable=self.ambient_var,
            command=self._on_ambient_toggle
        ).pack(side=tk.LEFT)
        
        self.genre_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row2,
            text="Auto Genre",
            variable=self.genre_var,
            command=self._on_genre_toggle
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        row3 = ttk.Frame(modes_frame)
        row3.pack(fill=tk.X, pady=(4, 0))
        
        self.spectrum_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row3,
            text="Spectrum",
            variable=self.spectrum_var,
            command=self._on_spectrum_toggle
        ).pack(side=tk.LEFT)
    
    def _create_advanced_tab(self):
        """Create the advanced status tab."""
        advanced_tab = ttk.Frame(self.notebook)
        self.notebook.add(advanced_tab, text="Status")
        
        # Create scrollable frame for status info
        status_container = ttk.Frame(advanced_tab, padding="5")
        status_container.pack(fill=tk.BOTH, expand=True)
        
        # Frequency levels display
        freq_frame = ttk.LabelFrame(status_container, text="Frequency Analysis", padding="5")
        freq_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Bass level
        bass_frame = ttk.Frame(freq_frame)
        bass_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(bass_frame, text="Bass:", width=8).pack(side=tk.LEFT)
        self.bass_bar = ttk.Progressbar(bass_frame, length=150, mode='determinate')
        self.bass_bar.pack(side=tk.LEFT, padx=(5, 0))
        self.bass_label = ttk.Label(bass_frame, text="0%", width=5)
        self.bass_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Mid level
        mid_frame = ttk.Frame(freq_frame)
        mid_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(mid_frame, text="Mid:", width=8).pack(side=tk.LEFT)
        self.mid_bar = ttk.Progressbar(mid_frame, length=150, mode='determinate')
        self.mid_bar.pack(side=tk.LEFT, padx=(5, 0))
        self.mid_label = ttk.Label(mid_frame, text="0%", width=5)
        self.mid_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # High level
        high_frame = ttk.Frame(freq_frame)
        high_frame.pack(fill=tk.X)
        ttk.Label(high_frame, text="High:", width=8).pack(side=tk.LEFT)
        self.high_bar = ttk.Progressbar(high_frame, length=150, mode='determinate')
        self.high_bar.pack(side=tk.LEFT, padx=(5, 0))
        self.high_label = ttk.Label(high_frame, text="0%", width=5)
        self.high_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Genre detection display
        genre_frame = ttk.LabelFrame(status_container, text="Genre Detection", padding="5")
        genre_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.genre_label = ttk.Label(genre_frame, text="Detecting...", font=('Arial', 10))
        self.genre_label.pack()
        
        # Build/Drop detection
        event_frame = ttk.LabelFrame(status_container, text="Event Detection", padding="5")
        event_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.event_label = ttk.Label(event_frame, text="Normal", font=('Arial', 10))
        self.event_label.pack()
        
        # DMX info
        dmx_frame = ttk.LabelFrame(status_container, text="DMX Info", padding="5")
        dmx_frame.pack(fill=tk.X)
        
        self.dmx_info_label = ttk.Label(
            dmx_frame,
            text=f"Universe: {config.DMX_UNIVERSE}\nChannels: {config.DMX_CHANNELS}\nFPS: {config.UPDATE_FPS}",
            font=('Arial', 9)
        )
        self.dmx_info_label.pack()
    
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
        elif label == "Beat Sens":
            self.beat_sensitivity_var = tk.DoubleVar(value=initial_value)
            var = self.beat_sensitivity_var
        elif label == "BPM Sync":
            self.bpm_sync_var = tk.DoubleVar(value=initial_value)
            var = self.bpm_sync_var
        elif label == "Chaos":
            self.chaos_var = tk.DoubleVar(value=initial_value)
            var = self.chaos_var
        elif label == "Echo":
            self.echo_var = tk.DoubleVar(value=initial_value)
            var = self.echo_var
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
        
        # Update advanced tab if it exists
        if hasattr(self, 'bass_bar'):
            # Update frequency bars
            bass_pct = int(state.get('bass', 0) * 100)
            mid_pct = int(state.get('mid', 0) * 100)
            high_pct = int(state.get('high', 0) * 100)
            
            self.bass_bar['value'] = bass_pct
            self.bass_label.config(text=f"{bass_pct}%")
            self.mid_bar['value'] = mid_pct
            self.mid_label.config(text=f"{mid_pct}%")
            self.high_bar['value'] = high_pct
            self.high_label.config(text=f"{high_pct}%")
            
            # Update genre label
            genre = state.get('genre', 'auto')
            self.genre_label.config(text=genre.capitalize())
            
            # Update event label
            if state.get('is_drop', False):
                self.event_label.config(text="DROP!", foreground='red')
            elif state.get('is_building', False):
                self.event_label.config(text="Building...", foreground='orange')
            else:
                self.event_label.config(text="Normal", foreground='black')
    
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
    
    def _on_beat_sensitivity_change(self, value):
        """Handle beat sensitivity slider change."""
        beat_sensitivity = float(value)
        if self.dmx_controller:
            self.dmx_controller.set_beat_sensitivity(beat_sensitivity)
    
    def _on_bpm_sync_change(self, value):
        """Handle BPM sync slider change."""
        # Map 0-1 slider to 0.25-2.0 (25% to 200%)
        bpm_sync = 0.25 + float(value) * 1.75
        if self.dmx_controller:
            self.dmx_controller.set_bpm_sync(bpm_sync)
    
    def _on_mood_match_toggle(self):
        """Handle mood match checkbox toggle."""
        enabled = self.mood_match_var.get()
        if self.dmx_controller:
            self.dmx_controller.set_mood_match(enabled)
    
    def _on_chaos_change(self, value):
        """Handle chaos slider change."""
        chaos = float(value)
        if self.dmx_controller:
            self.dmx_controller.set_chaos_level(chaos)
    
    def _on_echo_length_change(self, value):
        """Handle echo length slider change."""
        length = float(value) * 2.0  # Scale 0-1 to 0-2 seconds
        if self.dmx_controller:
            self.dmx_controller.set_echo_length(length)
            self.dmx_controller.set_echo_enabled(length > 0)
    
    def _on_theme_change(self, event=None):
        """Handle color theme selection."""
        theme = self.theme_var.get().lower()
        if theme == 'mono':
            theme = 'monochrome'
        if self.dmx_controller:
            self.dmx_controller.set_color_theme(theme)
    
    def _on_effect_change(self, event=None):
        """Handle effect mode selection."""
        effect = self.effect_var.get().lower()
        if self.dmx_controller:
            self.dmx_controller.set_effect_mode(effect)
    
    def _on_frequency_toggle(self):
        """Handle frequency mode toggle."""
        enabled = self.frequency_var.get()
        if self.dmx_controller:
            self.dmx_controller.set_frequency_mode(enabled)
    
    def _on_ambient_toggle(self):
        """Handle ambient mode toggle."""
        enabled = self.ambient_var.get()
        if self.dmx_controller:
            self.dmx_controller.set_ambient_mode(enabled)
    
    def _on_genre_toggle(self):
        """Handle genre auto toggle."""
        enabled = self.genre_var.get()
        if self.dmx_controller:
            self.dmx_controller.set_genre_auto(enabled)
    
    def _on_spectrum_toggle(self):
        """Handle spectrum mode toggle."""
        enabled = self.spectrum_var.get()
        if self.dmx_controller:
            self.dmx_controller.set_spectrum_mode(enabled)
    
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
    
    def _on_reset(self):
        """Reset all controls to default values."""
        # First, call the controller's reset method for a thorough reset
        if self.dmx_controller:
            self.dmx_controller.reset()
        
        # Reset all UI elements to match defaults
        self.smoothness_var.set(0.5)  # 0.5 = 50% smoothness (inverted)
        self.rainbow_var.set(0.5)  # 50% rainbow
        self.brightness_var.set(0.5)  # 50% brightness
        self.strobe_var.set(0.0)  # No strobe
        self.beat_sensitivity_var.set(0.5)  # 50% beat sensitivity
        if hasattr(self, 'bpm_sync_var'):
            self.bpm_sync_var.set(1.0)  # 100% BPM sync
        
        # Reset Effects tab controls if they exist
        if hasattr(self, 'chaos_var'):
            self.chaos_var.set(0.0)  # No chaos
        if hasattr(self, 'echo_var'):
            self.echo_var.set(0.0)  # No echo
        
        # Reset dropdowns
        self.theme_var.set("Default")
        self.effect_var.set("None")
        self.pattern_var.set("Wave")
        
        # Reset checkboxes
        self.mood_match_var.set(False)
        self.frequency_var.set(False)
        self.ambient_var.set(False)
        self.genre_var.set(False)
        if hasattr(self, 'spectrum_var'):
            self.spectrum_var.set(False)
        
        # Reset light count
        self.light_count_var.set(config.DEFAULT_LIGHT_COUNT)
        self.light_count_label.config(text=str(config.DEFAULT_LIGHT_COUNT))
        self.info_label.config(text=f"{config.DEFAULT_LIGHT_COUNT} PAR • DMX 1")
    
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