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
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Audio-Reactive DMX Lighting",
            font=('Arial', 20, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Audio Status", padding="15")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Audio active indicator
        self.status_indicator = tk.Canvas(status_frame, width=30, height=30)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 15))
        self.status_circle = self.status_indicator.create_oval(
            5, 5, 25, 25, fill='gray', outline='black'
        )
        
        # Status text
        self.status_text = ttk.Label(status_frame, text="Waiting for audio...", font=('Arial', 12))
        self.status_text.pack(side=tk.LEFT)
        
        # Metrics frame
        metrics_frame = ttk.LabelFrame(main_frame, text="Audio Metrics", padding="15")
        metrics_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # BPM display
        bpm_frame = ttk.Frame(metrics_frame)
        bpm_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(bpm_frame, text="BPM:", font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        self.bpm_label = ttk.Label(bpm_frame, text="0.0", font=('Arial', 14))
        self.bpm_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Intensity display with progress bar
        intensity_frame = ttk.Frame(metrics_frame)
        intensity_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(intensity_frame, text="Intensity:", font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        self.intensity_label = ttk.Label(intensity_frame, text="0%", font=('Arial', 14))
        self.intensity_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Intensity progress bar
        self.intensity_bar = ttk.Progressbar(
            metrics_frame,
            orient=tk.HORIZONTAL,
            length=300,
            mode='determinate',
            maximum=100
        )
        self.intensity_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Beat indicator (flashes on beat)
        self.beat_indicator_frame = ttk.Frame(metrics_frame)
        self.beat_indicator_frame.pack(fill=tk.X)
        ttk.Label(self.beat_indicator_frame, text="Beat:", font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        self.beat_canvas = tk.Canvas(self.beat_indicator_frame, width=20, height=20)
        self.beat_canvas.pack(side=tk.LEFT, padx=(10, 0))
        self.beat_circle = self.beat_canvas.create_oval(
            2, 2, 18, 18, fill='darkgray', outline='black'
        )
        
        # Lighting Mode Frame
        mode_frame = ttk.LabelFrame(main_frame, text="Lighting Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Create radio buttons for each mode
        self.mode_var = tk.StringVar(value=config.DEFAULT_LIGHTING_MODE)
        
        mode_buttons_frame = ttk.Frame(mode_frame)
        mode_buttons_frame.pack(fill=tk.X)
        
        for mode_key, mode_info in config.LIGHTING_MODES.items():
            rb = ttk.Radiobutton(
                mode_buttons_frame,
                text=mode_info['name'],
                variable=self.mode_var,
                value=mode_key,
                command=self._on_mode_change
            )
            rb.pack(side=tk.LEFT, padx=(0, 15))
        
        # Mode description label
        self.mode_description = ttk.Label(
            mode_frame,
            text=config.LIGHTING_MODES[config.DEFAULT_LIGHTING_MODE]['description'],
            font=('Arial', 10),
            foreground='gray'
        )
        self.mode_description.pack(pady=(5, 0))
        
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
        
        # Info label
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X)
        self.info_label = ttk.Label(
            info_frame,
            text="3 PAR Lights Connected • DMX Universe 1",
            font=('Arial', 10),
            foreground='gray'
        )
        self.info_label.pack()
    
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
        
        # Update BPM display
        self.bpm_label.config(text=f"{bpm:.1f}")
        
        # Update intensity display
        intensity_percent = int(intensity * 100)
        self.intensity_label.config(text=f"{intensity_percent}%")
        self.intensity_bar['value'] = intensity_percent
        
        # Update audio status indicator
        if audio_active:
            self.status_indicator.itemconfig(self.status_circle, fill='green')
            self.status_text.config(text="Audio detected - Playing")
        else:
            self.status_indicator.itemconfig(self.status_circle, fill='gray')
            self.status_text.config(text="No audio - Paused")
        
        # Flash beat indicator (check beat queue)
        if hasattr(self.audio_analyzer, 'last_beat_time'):
            import time
            time_since_beat = time.time() - self.audio_analyzer.last_beat_time
            if time_since_beat < 0.1:  # Flash for 100ms
                self.beat_canvas.itemconfig(self.beat_circle, fill='red')
            else:
                self.beat_canvas.itemconfig(self.beat_circle, fill='darkgray')
    
    def _on_mode_change(self):
        """Handle lighting mode change."""
        new_mode = self.mode_var.get()
        if self.dmx_controller:
            self.dmx_controller.set_mode(new_mode)
            # Update description
            self.mode_description.config(text=config.LIGHTING_MODES[new_mode]['description'])
    
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