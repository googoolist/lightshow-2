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
            # Bind escape key to exit fullscreen
            self.root.bind('<Escape>', lambda e: self._on_quit())
            # Cursor is visible by default - removed cursor="none"
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
        
        # Lighting Mode Buttons (top row)
        mode_frame = ttk.Frame(main_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create mode buttons
        self.mode_var = tk.StringVar(value=config.DEFAULT_LIGHTING_MODE)
        
        for mode_key, mode_info in config.LIGHTING_MODES.items():
            btn = ttk.Button(
                mode_frame,
                text=mode_info['name'],
                command=lambda m=mode_key: self._set_mode(m),
                width=12
            )
            btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # Highlight current mode
            if mode_key == config.DEFAULT_LIGHTING_MODE:
                btn.configure(style='Accent.TButton')
        
        self.mode_buttons = {}  # Store buttons for highlighting
        
        # Mode description (small text)
        self.mode_description = ttk.Label(
            main_frame,
            text=config.LIGHTING_MODES[config.DEFAULT_LIGHTING_MODE]['description'],
            font=('Arial', 9),
            foreground='gray'
        )
        self.mode_description.pack(pady=(0, 10))
        
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
        
        # Smoothness control frame
        smooth_frame = ttk.Frame(main_frame)
        smooth_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(smooth_frame, text="Smoothness:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        
        # Smoothness slider
        self.smoothness_var = tk.DoubleVar(value=0.5)  # Default middle position
        self.smoothness_slider = ttk.Scale(
            smooth_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.smoothness_var,
            command=self._on_smoothness_change,
            length=200
        )
        self.smoothness_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Smoothness labels
        ttk.Label(smooth_frame, text="Fast", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(smooth_frame, text="Smooth", font=('Arial', 9), foreground='gray').pack(side=tk.LEFT)
        
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
    
    def _set_mode(self, mode_key):
        """Set the lighting mode."""
        if self.dmx_controller:
            self.dmx_controller.set_mode(mode_key)
            self.mode_var.set(mode_key)
            # Update description
            self.mode_description.config(text=config.LIGHTING_MODES[mode_key]['description'])
    
    def _on_smoothness_change(self, value):
        """Handle smoothness slider change."""
        smoothness = float(value)
        if self.dmx_controller:
            self.dmx_controller.set_smoothness(smoothness)
    
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