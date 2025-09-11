"""
Audio capture and analysis module for beat detection, BPM estimation, and intensity measurement.
"""

import numpy as np
import sounddevice as sd
import aubio
import threading
import queue
import time
from collections import deque
import config


class AudioAnalyzer:
    def __init__(self, state_lock, beat_queue, stop_event):
        """
        Initialize the audio analyzer.
        
        Args:
            state_lock: Threading lock for shared state access
            beat_queue: Queue for beat events to lighting module
            stop_event: Threading event to signal shutdown
        """
        self.state_lock = state_lock
        self.beat_queue = beat_queue
        self.stop_event = stop_event
        
        # Shared state variables
        self.current_bpm = 0.0
        self.current_intensity = 0.0
        self.audio_active = False
        
        # Frequency analysis
        self.bass_intensity = 0.0
        self.mid_intensity = 0.0
        self.high_intensity = 0.0
        
        # Build-up/drop detection
        self.intensity_trend = deque(maxlen=30)  # Track 30 frames (~0.35s)
        self.is_building = False
        self.is_drop = False
        self.build_start_time = 0
        
        # Genre detection
        self.genre_hints = {
            'edm': 0, 'rock': 0, 'hiphop': 0, 'jazz': 0, 'ambient': 0
        }
        self.detected_genre = 'auto'
        
        # Audio analysis setup
        self.tempo_detector = aubio.tempo(
            "default",
            config.WIN_SIZE,
            config.HOP_SIZE,
            config.SAMPLE_RATE
        )
        
        # Beat tracking
        self.beat_timestamps = deque(maxlen=8)  # Keep last 8 beats for BPM calculation
        self.last_beat_time = 0
        
        # Intensity smoothing
        self.intensity_history = deque(maxlen=5)
        
        # Silence detection
        self.silent_frames = 0
        
        # Audio stream
        self.stream = None
        
    def start(self):
        """Start the audio analysis thread."""
        self.thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.thread.start()
        
    def _audio_loop(self):
        """Main audio processing loop running in separate thread."""
        try:
            # Open audio input stream
            self.stream = sd.InputStream(
                device=config.AUDIO_DEVICE_NAME,
                channels=1,
                samplerate=config.SAMPLE_RATE,
                blocksize=config.BUFFER_SIZE,
                dtype='float32',
                callback=None  # We'll use blocking read
            )
            
            self.stream.start()
            start_time = time.time()
            
            while not self.stop_event.is_set():
                try:
                    # Read audio block
                    audio_data, overflowed = self.stream.read(config.BUFFER_SIZE)
                    
                    if overflowed:
                        print("Audio buffer overflow detected")
                    
                    # Convert to mono float array
                    buffer = np.array(audio_data, dtype=np.float32).flatten()
                    
                    # Process with aubio for beat detection
                    current_time = time.time() - start_time
                    beat_detected = self.tempo_detector(buffer)
                    
                    if beat_detected:
                        self._handle_beat(current_time)
                    
                    # Calculate intensity (RMS)
                    rms = np.sqrt(np.mean(buffer**2))
                    self._update_intensity(rms)
                    
                    # Frequency analysis
                    self._analyze_frequencies(buffer)
                    
                    # Build-up/drop detection
                    self._detect_build_drop(self.current_intensity)
                    
                    # Genre detection
                    self._detect_genre(self.current_bpm, self.bass_intensity, beat_detected)
                    
                    # Check for silence/audio presence
                    self._update_audio_presence(rms)
                    
                    # Update shared state
                    self._update_shared_state()
                    
                except sd.PortAudioError as e:
                    print(f"Audio error: {e}")
                    time.sleep(0.1)  # Brief pause before retry
                    
        except Exception as e:
            print(f"Audio thread error: {e}")
        finally:
            if self.stream:
                self.stream.stop()
                self.stream.close()
    
    def _handle_beat(self, current_time):
        """Process a detected beat."""
        # Avoid double-triggering beats too close together
        if current_time - self.last_beat_time < 0.1:  # Min 100ms between beats
            return
            
        self.last_beat_time = current_time
        self.beat_timestamps.append(current_time)
        
        # Calculate BPM from recent beats
        if len(self.beat_timestamps) >= 2:
            intervals = []
            for i in range(1, len(self.beat_timestamps)):
                interval = self.beat_timestamps[i] - self.beat_timestamps[i-1]
                if 0.2 < interval < 2.0:  # Reasonable beat interval range
                    intervals.append(interval)
            
            if intervals:
                # Use median interval for stability
                median_interval = np.median(intervals)
                bpm = 60.0 / median_interval
                
                # Clamp to reasonable range
                bpm = max(config.MIN_BPM, min(config.MAX_BPM, bpm))
                self.current_bpm = bpm
        
        # Send beat event to lighting module
        self.beat_queue.put({
            'timestamp': current_time,
            'bpm': self.current_bpm,
            'intensity': self.current_intensity
        })
    
    def _update_intensity(self, rms):
        """Update and smooth the intensity measurement."""
        # Add to history for smoothing
        self.intensity_history.append(rms)
        
        if len(self.intensity_history) > 0:
            # Apply smoothing
            smoothed = np.mean(self.intensity_history)
            
            # Apply exponential smoothing with previous value
            # Use a default smoothing value for audio analysis (independent of lighting modes)
            smoothing_factor = 0.7
            self.current_intensity = (
                smoothing_factor * self.current_intensity +
                (1 - smoothing_factor) * smoothed
            )
            
            # Normalize to 0-1 range (assuming max RMS of 1.0 for float audio)
            self.current_intensity = min(1.0, self.current_intensity)
    
    def _update_audio_presence(self, rms):
        """Detect if audio is playing or paused."""
        if rms < config.SILENCE_THRESHOLD:
            self.silent_frames += 1
        else:
            self.silent_frames = 0
        
        # Update audio active status
        self.audio_active = self.silent_frames < config.SILENCE_FRAME_COUNT
    
    def _update_shared_state(self):
        """Update the shared state variables with thread lock."""
        with self.state_lock:
            # These will be read by other threads
            pass  # State is already updated in instance variables
    
    def _analyze_frequencies(self, samples):
        """Analyze frequency content of audio samples."""
        # Perform FFT
        fft = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(len(samples), 1/config.SAMPLE_RATE)
        magnitude = np.abs(fft)
        
        # Define frequency bands
        bass_mask = (freqs >= 20) & (freqs <= 250)
        mid_mask = (freqs > 250) & (freqs <= 4000)
        high_mask = (freqs > 4000) & (freqs <= 20000)
        
        # Calculate intensity for each band
        if np.any(bass_mask):
            self.bass_intensity = np.mean(magnitude[bass_mask]) / 1000
        if np.any(mid_mask):
            self.mid_intensity = np.mean(magnitude[mid_mask]) / 500
        if np.any(high_mask):
            self.high_intensity = np.mean(magnitude[high_mask]) / 250
            
        # Normalize to 0-1 range
        self.bass_intensity = min(1.0, self.bass_intensity)
        self.mid_intensity = min(1.0, self.mid_intensity)
        self.high_intensity = min(1.0, self.high_intensity)
    
    def _detect_build_drop(self, intensity):
        """Detect build-ups and drops in the music."""
        self.intensity_trend.append(intensity)
        
        if len(self.intensity_trend) < 10:
            return
            
        # Calculate trend
        recent = list(self.intensity_trend)[-10:]
        older = list(self.intensity_trend)[:-10] if len(self.intensity_trend) > 10 else recent
        
        recent_avg = np.mean(recent)
        older_avg = np.mean(older) if older else recent_avg
        
        # Detect build-up (gradual increase)
        if recent_avg > older_avg * 1.2 and not self.is_building:
            self.is_building = True
            self.build_start_time = time.time()
            
        # Detect drop (sudden increase after build)
        if self.is_building and intensity > recent_avg * 1.5:
            self.is_drop = True
            self.is_building = False
            # Drop will auto-clear after 1 second
            
        # Clear drop flag after 1 second
        if self.is_drop and time.time() - self.build_start_time > 1.0:
            self.is_drop = False
    
    def _detect_genre(self, bpm, bass_intensity, has_beat):
        """Simple genre detection based on musical characteristics."""
        # Reset hints gradually
        for genre in self.genre_hints:
            self.genre_hints[genre] *= 0.99
            
        # EDM: Fast BPM, strong bass, regular beats
        if 120 <= bpm <= 140 and bass_intensity > 0.6 and has_beat:
            self.genre_hints['edm'] += 0.1
            
        # Hip-Hop: Medium BPM, very strong bass
        if 80 <= bpm <= 100 and bass_intensity > 0.7:
            self.genre_hints['hiphop'] += 0.1
            
        # Rock: Medium-fast BPM, balanced frequencies  
        if 100 <= bpm <= 140 and 0.3 < bass_intensity < 0.7:
            self.genre_hints['rock'] += 0.1
            
        # Jazz: Variable BPM, complex patterns
        if 60 <= bpm <= 150 and not has_beat:
            self.genre_hints['jazz'] += 0.05
            
        # Ambient: Slow or no clear BPM, low intensity
        if (bpm < 80 or bpm == 0) and bass_intensity < 0.3:
            self.genre_hints['ambient'] += 0.1
            
        # Determine dominant genre
        max_score = max(self.genre_hints.values())
        if max_score > 0.5:
            for genre, score in self.genre_hints.items():
                if score == max_score:
                    self.detected_genre = genre
                    break
    
    def get_state(self):
        """Get current audio state (thread-safe)."""
        with self.state_lock:
            return {
                'bpm': self.current_bpm,
                'intensity': self.current_intensity,
                'audio_active': self.audio_active,
                'bass': self.bass_intensity,
                'mid': self.mid_intensity,
                'high': self.high_intensity,
                'is_building': self.is_building,
                'is_drop': self.is_drop,
                'genre': self.detected_genre
            }
    
    def stop(self):
        """Stop the audio analysis thread."""
        self.stop_event.set()
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)