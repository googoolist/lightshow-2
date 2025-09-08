#!/usr/bin/env python3
"""
DMX Interface Test - Verify OLA and DMX hardware configuration
"""

import sys
import time
import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from ola.ClientWrapper import ClientWrapper
    print("✓ OLA Python bindings imported successfully")
except ImportError as e:
    print(f"✗ Failed to import OLA: {e}")
    print("  Run: ./link_ola.sh")
    sys.exit(1)

def test_ola_connection():
    """Test OLA daemon connection."""
    print("\n1. Testing OLA Connection")
    print("-" * 30)
    
    try:
        wrapper = ClientWrapper()
        client = wrapper.Client()
        print("✓ Connected to OLA daemon")
        
        # Test universe info
        print("\n2. Checking Universe Configuration")
        print("-" * 30)
        
        test_universe = 1
        print(f"Testing universe {test_universe}...")
        
        # Send test data to verify universe is active
        test_data = array.array('B', [0] * 512)
        success = [False]
        
        def callback(status):
            if status.Succeeded():
                success[0] = True
                print(f"✓ Universe {test_universe} is active and accepting data")
            else:
                print(f"✗ Universe {test_universe} failed: {status}")
        
        client.SendDmx(test_universe, test_data, callback)
        
        # Give callback time to execute
        time.sleep(0.5)
        
        if not success[0]:
            print(f"\n✗ Universe {test_universe} is not responding!")
            print("  Check OLA web interface: http://localhost:9090")
            print("  - Is universe 1 active?")
            print("  - Is your DMX device patched to universe 1?")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Failed to connect to OLA daemon: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if OLA daemon is running:")
        print("     sudo systemctl status olad")
        print("  2. Start OLA if needed:")
        print("     sudo systemctl start olad")
        print("  3. Check OLA web interface:")
        print("     http://localhost:9090")
        return False

def test_dmx_output():
    """Test actual DMX output with visual feedback."""
    print("\n3. DMX Output Test")
    print("-" * 30)
    print("This will test each PAR light individually")
    print("Watch your lights for response...\n")
    
    wrapper = ClientWrapper()
    client = wrapper.Client()
    
    # Track if we get any response
    got_response = False
    
    def send_and_maintain(data, duration=2):
        """Send DMX data and maintain it for duration."""
        end_time = time.time() + duration
        send_count = [0]
        
        def send_frame():
            if time.time() < end_time:
                client.SendDmx(1, data, lambda s: None)
                send_count[0] += 1
                # Send at 30 FPS
                wrapper.AddEvent(33, send_frame)
            else:
                # Stop after duration
                wrapper.Stop()
        
        # Start sending
        wrapper.AddEvent(0, send_frame)
        wrapper.Run()
        print(f"  Sent {send_count[0]} frames in {duration} seconds")
    
    # Test patterns for different DMX modes
    test_configs = [
        {
            "name": "3-channel RGB mode",
            "channels": [
                (1, 2, 3),    # PAR 1: RGB on channels 1-3
                (4, 5, 6),    # PAR 2: RGB on channels 4-6
                (7, 8, 9),    # PAR 3: RGB on channels 7-9
            ]
        },
        {
            "name": "4-channel RGBW mode", 
            "channels": [
                (1, 2, 3, 4),     # PAR 1: RGBW on channels 1-4
                (5, 6, 7, 8),     # PAR 2: RGBW on channels 5-8
                (9, 10, 11, 12),  # PAR 3: RGBW on channels 9-12
            ]
        },
        {
            "name": "7-channel mode (with dimmer)",
            "channels": [
                (1, 2, 3, 4, 5, 6, 7),     # PAR 1
                (8, 9, 10, 11, 12, 13, 14), # PAR 2
                (15, 16, 17, 18, 19, 20, 21), # PAR 3
            ]
        },
        {
            "name": "Current config.py settings",
            "channels": [
                tuple(range(1, 9)),   # PAR 1: channels 1-8
                tuple(range(9, 17)),  # PAR 2: channels 9-16
                tuple(range(17, 25)), # PAR 3: channels 17-24
            ]
        }
    ]
    
    print("Testing different DMX channel configurations...")
    print("Press Ctrl+C if you see your lights respond!\n")
    
    for config_idx, config in enumerate(test_configs):
        print(f"\nTest {config_idx + 1}: {config['name']}")
        print("-" * 40)
        
        for par_idx, channels in enumerate(config['channels']):
            print(f"\nPAR {par_idx + 1} - Testing channels {channels[0]}-{channels[-1]}")
            
            # Create DMX frame
            data = array.array('B', [0] * 32)
            
            # Set all channels for this PAR to 255
            for ch in channels:
                if ch <= 32:  # Stay within our array bounds
                    data[ch - 1] = 255
            
            print(f"  Setting channels {list(channels)} to 255")
            print(f"  DMX data: {list(data[:24])}")
            
            # Send for 2 seconds
            send_and_maintain(data, 2)
            
            # Brief pause between tests
            time.sleep(0.5)
            
            response = input("  Did PAR {} light up? (y/n/s to skip): ".format(par_idx + 1))
            if response.lower() == 'y':
                got_response = True
                print(f"  ✓ Found working configuration for PAR {par_idx + 1}!")
                print(f"    Channels: {channels}")
            elif response.lower() == 's':
                break
        
        if got_response:
            print(f"\n✓ Working configuration found: {config['name']}")
            print("  Update your config.py with the correct channel mappings")
            break
    
    # Turn all off
    print("\nTurning all lights OFF...")
    off_data = array.array('B', [0] * 32)
    client.SendDmx(1, off_data, lambda s: None)
    
    return got_response

def main():
    print("=" * 50)
    print("DMX INTERFACE TEST")
    print("=" * 50)
    
    # Test OLA connection
    if not test_ola_connection():
        print("\n✗ OLA connection failed. Fix this first.")
        sys.exit(1)
    
    # Test DMX output
    print("\nPress Enter to start DMX output tests...")
    input()
    
    if test_dmx_output():
        print("\n✓ DMX interface is working!")
        print("\nNext steps:")
        print("1. Update config.py with the correct channel mappings")
        print("2. Run ./run.sh to start the audio-reactive system")
    else:
        print("\n✗ No DMX response detected")
        print("\nTroubleshooting:")
        print("1. Check DMX cable connections")
        print("2. Verify PAR lights are in DMX mode (not auto/sound mode)")
        print("3. Check PAR light DMX addresses")
        print("4. Try different DMX termination (add/remove terminator)")

if __name__ == "__main__":
    main()