#!/usr/bin/env python3
"""
Continuous DMX test - keeps sending frames to maintain light state
"""

import sys
import time
import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ola.ClientWrapper import ClientWrapper

def continuous_dmx_test():
    """Send continuous DMX frames to keep lights on."""
    print("Continuous DMX Test")
    print("==================")
    print("This will send continuous DMX frames to keep lights on")
    print("Press Ctrl+C to stop")
    
    wrapper = ClientWrapper()
    client = wrapper.Client()
    
    # Test pattern - all channels at different levels
    test_patterns = [
        ("All channels 1-8 at FULL", [255, 255, 255, 255, 255, 255, 255, 255] + [0] * 16),
        ("Simple RGB test", [255, 255, 0, 0] + [0] * 20),  # Red on first fixture
        ("All channels moderate", [128] * 24),  # All at 50%
    ]
    
    pattern_index = 0
    frame_count = 0
    
    def send_frame():
        nonlocal frame_count, pattern_index
        
        # Change pattern every 100 frames (about 3 seconds at 30fps)
        if frame_count % 100 == 0:
            name, values = test_patterns[pattern_index % len(test_patterns)]
            print(f"\nPattern: {name}")
            print(f"DMX values: {values[:12]}...")  # Show first 12 channels
            pattern_index += 1
        
        # Get current pattern
        _, values = test_patterns[(pattern_index - 1) % len(test_patterns)]
        data = array.array('B', values)
        
        # Send DMX
        client.SendDmx(1, data, lambda status: None)
        
        frame_count += 1
        
        # Schedule next frame (30 FPS)
        wrapper.AddEvent(33, send_frame)
    
    # Start sending frames
    wrapper.AddEvent(0, send_frame)
    
    try:
        # Run event loop
        wrapper.Run()
    except KeyboardInterrupt:
        print("\nStopping...")
        # Send all zeros before stopping
        off_data = array.array('B', [0] * 24)
        client.SendDmx(1, off_data, lambda status: None)
        wrapper.Stop()

if __name__ == "__main__":
    continuous_dmx_test()