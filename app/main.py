#!/usr/bin/env python3
"""
Main orchestration script for the audio-reactive DMX lighting system.
Coordinates audio analysis, DMX control, and GUI modules.
"""

import sys
import threading
import queue
import signal
import time
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import config
from audio import AudioAnalyzer
from lighting import DmxController
from ui import AudioReactiveLightingGUI


class AudioReactiveLightingSystem:
    def __init__(self, headless=False):
        """
        Initialize the complete audio-reactive lighting system.
        
        Args:
            headless: If True, run without GUI (for testing/debugging)
        """
        self.headless = headless
        
        # Thread synchronization
        self.state_lock = threading.Lock()
        self.beat_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        # System components
        self.audio_analyzer = None
        self.dmx_controller = None
        self.gui = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start all system components."""
        print("Starting Audio-Reactive DMX Lighting System...")
        print(f"Configuration: {len(config.LIGHT_FIXTURES)} PAR lights on DMX Universe {config.DMX_UNIVERSE}")
        
        try:
            # Initialize audio analyzer
            print("Initializing audio analyzer...")
            self.audio_analyzer = AudioAnalyzer(
                self.state_lock,
                self.beat_queue,
                self.stop_event
            )
            self.audio_analyzer.start()
            print("Audio analyzer started")
            
            # Initialize DMX controller
            print("Initializing DMX controller...")
            self.dmx_controller = DmxController(
                self.audio_analyzer,
                self.beat_queue,
                self.stop_event
            )
            self.dmx_controller.start()
            print("DMX controller started")
            
            if not self.headless:
                # Initialize and run GUI (blocks until window closed)
                print("Starting GUI...")
                self.gui = AudioReactiveLightingGUI(
                    self.audio_analyzer,
                    self.dmx_controller,
                    self.stop_event
                )
                self.gui.run()
            else:
                # Headless mode - just wait for stop signal
                print("Running in headless mode. Press Ctrl+C to stop.")
                try:
                    while not self.stop_event.is_set():
                        time.sleep(1)
                        # Print status periodically in headless mode
                        state = self.audio_analyzer.get_state()
                        print(f"BPM: {state['bpm']:.1f} | "
                              f"Intensity: {state['intensity']:.2%} | "
                              f"Audio: {'Active' if state['audio_active'] else 'Paused'}")
                except KeyboardInterrupt:
                    pass
            
        except Exception as e:
            print(f"Error during startup: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    def stop(self):
        """Stop all system components gracefully."""
        print("Stopping system...")
        
        # Signal all threads to stop
        self.stop_event.set()
        
        # Stop components in reverse order
        if self.dmx_controller:
            print("Stopping DMX controller...")
            self.dmx_controller.stop()
        
        if self.audio_analyzer:
            print("Stopping audio analyzer...")
            self.audio_analyzer.stop()
        
        print("System stopped")


def check_dependencies():
    """Check if required dependencies are installed."""
    missing_deps = []
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import sounddevice
    except ImportError:
        missing_deps.append("sounddevice")
    
    try:
        import aubio
    except ImportError:
        missing_deps.append("aubio")
    
    try:
        from ola import ClientWrapper
    except ImportError:
        missing_deps.append("ola (install via: sudo apt-get install ola ola-python)")
    
    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstall with: pip install numpy sounddevice aubio")
        print("For OLA: sudo apt-get install ola ola-python")
        return False
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Audio-Reactive DMX Lighting Controller for Raspberry Pi"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without GUI (for testing/debugging)"
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check dependencies and exit"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    if args.check_deps or not check_dependencies():
        if args.check_deps:
            print("All dependencies are installed!" if check_dependencies() else "")
        sys.exit(0 if args.check_deps and check_dependencies() else 1)
    
    # Check if OLA daemon is running
    try:
        from ola.ClientWrapper import ClientWrapper
        wrapper = ClientWrapper()
        # This will fail if olad is not running
        wrapper.Stop()
    except:
        print("Warning: OLA daemon (olad) does not appear to be running.")
        print("Start it with: sudo olad")
        print("Configure DMX dongle at: http://localhost:9090")
        print("")
    
    # Start the system
    system = AudioReactiveLightingSystem(headless=args.headless)
    system.start()


if __name__ == "__main__":
    main()