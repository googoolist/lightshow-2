"""
Main UI wrapper with mode switching between Simple and Advanced modes.
"""

import tkinter as tk
from tkinter import ttk
import config
from ui_simple import SimpleUI
from ui_advanced import AudioReactiveLightingGUI as AdvancedUI


class MainUI:
    """Main UI with mode switching capability."""
    
    def __init__(self, audio_analyzer, simple_controller, advanced_controller, stop_event):
        """
        Initialize the main UI.
        
        Args:
            audio_analyzer: Reference to audio analyzer
            simple_controller: Simple mode DMX controller
            advanced_controller: Advanced mode DMX controller
            stop_event: Threading event to signal shutdown
        """
        self.audio_analyzer = audio_analyzer
        self.simple_controller = simple_controller
        self.advanced_controller = advanced_controller
        self.stop_event = stop_event
        
        # Current mode
        self.current_mode = "simple"  # Start in simple mode
        self.current_ui = None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Lightshow Control")
        
        # Set window size
        if config.FULLSCREEN:
            self.root.attributes('-fullscreen', True)
            self.root.bind('<Escape>', lambda e: self._on_quit())
            self.root.bind('<q>', lambda e: self._on_quit())
            self.root.bind('<Q>', lambda e: self._on_quit())
        else:
            self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
            
        # Configure window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Create main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create mode selector at top
        self._create_mode_selector()
        
        # Create content frame for UI
        self.content_frame = ttk.Frame(self.main_container)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Load initial UI (simple mode)
        self._switch_to_simple()
        
    def _create_mode_selector(self):
        """Create the mode selection controls at the top."""
        # Mode selector frame
        mode_frame = ttk.Frame(self.main_container, relief=tk.RAISED, borderwidth=1)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Mode label
        ttk.Label(
            mode_frame,
            text="Mode:",
            font=('Arial', 10, 'bold')
        ).pack(side=tk.LEFT, padx=(10, 5))
        
        # Radio buttons for mode selection
        self.mode_var = tk.StringVar(value="simple")
        
        self.simple_radio = ttk.Radiobutton(
            mode_frame,
            text="Simple",
            variable=self.mode_var,
            value="simple",
            command=self._on_mode_change
        )
        self.simple_radio.pack(side=tk.LEFT, padx=(0, 5))
        
        self.advanced_radio = ttk.Radiobutton(
            mode_frame,
            text="Advanced",
            variable=self.mode_var,
            value="advanced",
            command=self._on_mode_change
        )
        self.advanced_radio.pack(side=tk.LEFT, padx=(0, 10))
        
        # Quit button (right side)
        self.quit_button = ttk.Button(
            mode_frame,
            text="Quit",
            command=self._on_quit
        )
        self.quit_button.pack(side=tk.RIGHT, padx=(0, 10))
        
    def _on_mode_change(self):
        """Handle mode selection change."""
        new_mode = self.mode_var.get()
        
        if new_mode == self.current_mode:
            return  # No change
            
        if new_mode == "simple":
            self._switch_to_simple()
        else:
            self._switch_to_advanced()
            
    def _switch_to_simple(self):
        """Switch to simple mode UI."""
        # Clear current UI
        self._clear_content_frame()
        
        # Update mode
        self.current_mode = "simple"
        
        # Stop advanced controller if running
        if self.advanced_controller and hasattr(self.advanced_controller, 'stop'):
            # Don't actually stop the thread, just pause it
            pass
            
        # Start simple controller
        if self.simple_controller and not hasattr(self.simple_controller, 'thread'):
            self.simple_controller.start()
            
        # Create simple UI
        self.current_ui = SimpleUI(
            self.content_frame,
            self.audio_analyzer,
            self.simple_controller,
            self.stop_event
        )
        
    def _switch_to_advanced(self):
        """Switch to advanced mode UI."""
        # Clear current UI
        self._clear_content_frame()
        
        # Update mode
        self.current_mode = "advanced"
        
        # Stop simple controller if running
        if self.simple_controller and hasattr(self.simple_controller, 'stop'):
            # Don't actually stop the thread, just pause it
            pass
            
        # Start advanced controller
        if self.advanced_controller and not hasattr(self.advanced_controller, 'thread'):
            self.advanced_controller.start()
            
        # Create advanced UI (it creates its own window structure)
        # We need to embed it in our content frame
        self._create_embedded_advanced_ui()
        
    def _create_embedded_advanced_ui(self):
        """Create advanced UI embedded in content frame."""
        # The advanced UI expects to create its own window, so we need to adapt it
        # For now, we'll create a simplified version that works with our frame
        
        # Import the advanced UI module
        from ui_advanced import AudioReactiveLightingGUI
        
        # Create instance but prevent it from creating its own window
        class EmbeddedAdvancedUI:
            def __init__(self, parent_frame, audio_analyzer, dmx_controller, stop_event):
                self.audio_analyzer = audio_analyzer
                self.dmx_controller = dmx_controller
                self.stop_event = stop_event
                self.root = parent_frame  # Use our frame as root
                
                # Copy the widget creation from advanced UI
                advanced = AudioReactiveLightingGUI.__new__(AudioReactiveLightingGUI)
                advanced.audio_analyzer = audio_analyzer
                advanced.dmx_controller = dmx_controller
                advanced.stop_event = stop_event
                advanced.root = parent_frame
                
                # Call the widget creation method
                advanced._create_widgets()
                advanced._initialize_controller()
                
                # Store reference
                self.advanced_ui = advanced
                
                # Start updates
                self._schedule_update()
                
            def _schedule_update(self):
                if hasattr(self, 'advanced_ui'):
                    self.advanced_ui._update_display()
                if not self.stop_event.is_set():
                    self.root.after(config.GUI_UPDATE_INTERVAL, self._schedule_update)
                    
            def destroy(self):
                pass
                
        self.current_ui = EmbeddedAdvancedUI(
            self.content_frame,
            self.audio_analyzer,
            self.advanced_controller,
            self.stop_event
        )
        
    def _clear_content_frame(self):
        """Clear the content frame of all widgets."""
        if self.current_ui and hasattr(self.current_ui, 'destroy'):
            self.current_ui.destroy()
            
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
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