#!/usr/bin/env python3
"""
Simple DMX test script to verify OLA and light communication
"""

import sys
import time
import array
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ola.ClientWrapper import ClientWrapper
import config

def test_dmx():
    """Test DMX output with simple patterns."""
    print("DMX Test Script")
    print("===============")
    print(f"Testing Universe: {config.DMX_UNIVERSE}")
    print(f"Testing {len(config.LIGHT_FIXTURES)} PAR lights")
    
    # Setup OLA
    wrapper = ClientWrapper()
    client = wrapper.Client()
    
    def send_dmx(data):
        """Send DMX data and wait."""
        client.SendDmx(config.DMX_UNIVERSE, data, lambda status: 
                      print(f"Send status: {'OK' if status.Succeeded() else 'FAILED'}"))
    
    # Test 1: All channels off
    print("\nTest 1: All OFF")
    data = array.array('B', [0] * 24)
    send_dmx(data)
    time.sleep(2)
    
    # Test 2: Turn on each PAR individually with white
    for i, fixture in enumerate(config.LIGHT_FIXTURES):
        print(f"\nTest 2.{i+1}: PAR {i+1} WHITE (channels {fixture['start_channel']}-{fixture['start_channel']+7})")
        data = array.array('B', [0] * 24)
        
        base = fixture['start_channel'] - 1  # Convert to 0-indexed
        channels = fixture['channels']
        
        # Set dimmer to full
        if 'dimmer' in channels:
            data[base + channels['dimmer']] = 255
            print(f"  Setting channel {base + channels['dimmer'] + 1} (dimmer) = 255")
        
        # Set RGB to white
        if 'red' in channels:
            data[base + channels['red']] = 255
            print(f"  Setting channel {base + channels['red'] + 1} (red) = 255")
        if 'green' in channels:
            data[base + channels['green']] = 255
            print(f"  Setting channel {base + channels['green'] + 1} (green) = 255")
        if 'blue' in channels:
            data[base + channels['blue']] = 255
            print(f"  Setting channel {base + channels['blue'] + 1} (blue) = 255")
        
        print(f"  DMX data: {list(data)}")
        send_dmx(data)
        time.sleep(2)
    
    # Test 3: All PARs RED
    print("\nTest 3: All PARs RED")
    data = array.array('B', [0] * 24)
    for fixture in config.LIGHT_FIXTURES:
        base = fixture['start_channel'] - 1
        channels = fixture['channels']
        if 'dimmer' in channels:
            data[base + channels['dimmer']] = 255
        if 'red' in channels:
            data[base + channels['red']] = 255
    print(f"  DMX data: {list(data)}")
    send_dmx(data)
    time.sleep(2)
    
    # Test 4: Simple channel test (raw)
    print("\nTest 4: Raw channel test - channels 1-8 at 255")
    data = array.array('B', [255] * 8 + [0] * 16)
    print(f"  DMX data: {list(data)}")
    send_dmx(data)
    time.sleep(2)
    
    # Turn off
    print("\nTurning all OFF")
    data = array.array('B', [0] * 24)
    send_dmx(data)
    
    # Stop OLA wrapper
    wrapper.Stop()
    print("\nTest complete!")

if __name__ == "__main__":
    test_dmx()