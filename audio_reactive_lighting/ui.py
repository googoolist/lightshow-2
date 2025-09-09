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
        
        # Start periodic updates
        self._schedule_update()
    
    def _create_widgets(self):
        """Create all GUI widgets - compact design for small screens."""
        # Main container with less padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Combined status and metrics frame (no header)
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Audio active indicator with status text
        indicator_frame = ttk.Frame(status_frame)
        indicator_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        self.status_indicator = tk.Canvas(indicator_frame, width=20, height=20)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 5))
        self.status_circle = self.status_indicator.create_oval(
            2, 2, 18, 18, fill='gray', outline='black'
        )
        
        self.status_text = ttk.Label(indicator_frame, text="No Audio", font=('Arial', 10))
        self.status_text.pack(side=tk.LEFT)
        
        # BPM display (compact)
        bpm_frame = ttk.Frame(status_frame)
        bpm_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(bpm_frame, text="BPM:", font=('Arial', 11, 'bold')).pack(side=tk.LEFT)
        self.bpm_label = ttk.Label(bpm_frame, text="0", font=('Arial', 11))
        self.bpm_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Intensity display (compact)
        intensity_frame = ttk.Frame(status_frame)
        intensity_frame.pack(side=tk.LEFT)
        ttk.Label(intensity_frame, text="Level:", font=('Arial', 11, 'bold')).pack(side=tk.LEFT)
        self.intensity_label = ttk.Label(intensity_frame, text="0%", font=('Arial', 11))
        self.intensity_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Speed control frame
        speed_frame = ttk.Frame(main_frame)
        speed_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(speed_frame, text="Speed:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        
        # Speed slider (inverted smoothness - 0=slow, 1=fast)
        self.smoothness_var = tk.DoubleVar(value=0.5)  # Default middle position
        self.speed_slider = ttk.Scale(
            speed_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.smoothness_var,
            command=self._on_smoothness_change,
            length=200
        )
        self.speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Speed labels
        ttk.Label(speed_frame, text="Slow", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(speed_frame, text="Fast", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT)
        
        # Rainbow control frame
        rainbow_frame = ttk.Frame(main_frame)
        rainbow_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(rainbow_frame, text="Rainbow:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        
        # Rainbow slider (0=single color, 1=full rainbow)
        self.rainbow_var = tk.DoubleVar(value=0.5)  # Default middle position
        self.rainbow_slider = ttk.Scale(
            rainbow_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.rainbow_var,
            command=self._on_rainbow_change,
            length=200
        )
        self.rainbow_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Rainbow labels
        ttk.Label(rainbow_frame, text="Single", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(rainbow_frame, text="Full", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT)
        
        # Color Temperature control frame
        temp_frame = ttk.Frame(main_frame)
        temp_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(temp_frame, text="Color Temp:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        
        # Color Temperature slider (0=warm, 1=cool)
        self.color_temp_var = tk.DoubleVar(value=0.5)  # Default middle position
        self.color_temp_slider = ttk.Scale(
            temp_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.color_temp_var,
            command=self._on_color_temp_change,
            length=200
        )
        self.color_temp_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Color Temp labels
        ttk.Label(temp_frame, text="Warm", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(temp_frame, text="Cool", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT)
        
        # Strobe control frame
        strobe_frame = ttk.Frame(main_frame)
        strobe_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(strobe_frame, text="Strobe:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        
        # Strobe slider (0=off, 1=max)
        self.strobe_var = tk.DoubleVar(value=0.0)  # Default off
        self.strobe_slider = ttk.Scale(
            strobe_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.strobe_var,
            command=self._on_strobe_change,
            length=200
        )
        self.strobe_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Strobe labels
        ttk.Label(strobe_frame, text="Off", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(strobe_frame, text="Max", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT)
        
        # Pattern control frame
        pattern_frame = ttk.Frame(main_frame)
        pattern_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(pattern_frame, text="Pattern:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        
        # Pattern selector dropdown
        self.pattern_var = tk.StringVar(value="sync")
        self.pattern_combo = ttk.Combobox(
            pattern_frame,
            textvariable=self.pattern_var,
            values=["Sync", "Wave", "Center", "Alternate", "Mirror"],
            state="readonly",
            width=15
        )
        self.pattern_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.pattern_combo.bind("<<ComboboxSelected>>", self._on_pattern_change)
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Quit button
        self.quit_button = ttk.Button(
            control_frame,
            text="Quit",
            command=self._on_quit,
            style='Accent.TButton'
        )
        self.quit_button.pack(side=tk.RIGHT)
        
        # Configure accent button style
        self.style.configure('Accent.TButton', font=('Arial', 12, 'bold'))
        
        # Info label (compact)
        self.info_label = ttk.Label(
            main_frame,
            text="3 PAR Lights • DMX Universe 1",
            font=('Arial', 9),
            foreground='gray'
        )
        self.info_label.pack(pady=(5, 0))
    
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
    
    def _on_color_temp_change(self, value):
        """Handle color temperature slider change."""
        color_temp = float(value)
        if self.dmx_controller:
            self.dmx_controller.set_color_temperature(color_temp)
    
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
    
    def _on_quit(self)
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