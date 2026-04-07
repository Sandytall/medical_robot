"""
Mock Audio Implementation for Development
"""
import numpy as np
import time
from typing import Optional, List, Dict, Any

from ..interfaces.audio_interface import AudioInterface


class MockAudio(AudioInterface):
    """Mock audio implementation for speaker and microphone"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Audio settings
        self.volume = 0.7
        self.microphone_gain = 0.5
        self.sample_rate = 16000
        self.is_muted = False

        # Recording state
        self.is_recording_flag = False
        self.recorded_data = None
        self.recording_start_time = None

        # Available voices and sound effects
        self.voices = ['default', 'male', 'female', 'child', 'robot']
        self.sound_effects = ['beep', 'alert', 'success', 'error', 'notification', 'startup']

        # Audio devices simulation
        self.audio_devices = {
            'input': ['Mock Microphone 1', 'Mock USB Mic', 'Mock Webcam Mic'],
            'output': ['Mock Speakers', 'Mock USB Speaker', 'Mock HDMI Audio']
        }

        self.current_input_device = self.audio_devices['input'][0]
        self.current_output_device = self.audio_devices['output'][0]

        self.is_initialized = False

    def initialize(self) -> bool:
        """Initialize audio hardware"""
        self.is_initialized = True
        print("Mock audio system initialized")
        print(f"Input device: {self.config.get('input_device', 'Default')}")
        print(f"Output device: {self.config.get('output_device', 'Default')}")
        print(f"Sample rate: {self.sample_rate} Hz")
        return True

    def play_text(self, text: str, voice: str = "default") -> bool:
        """Convert text to speech and play"""
        if not self.is_initialized or self.is_muted:
            return False

        if voice not in self.voices:
            voice = "default"

        # Simulate text-to-speech processing time
        processing_time = max(0.5, len(text) * 0.05)  # 50ms per character minimum 500ms

        print(f"Mock TTS [{voice}]: '{text}' (volume: {self.volume:.1f}, duration: {processing_time:.1f}s)")

        # Simulate audio playback
        time.sleep(min(processing_time, 3.0))  # Cap at 3 seconds for responsiveness
        return True

    def play_audio_file(self, file_path: str) -> bool:
        """Play audio file"""
        if not self.is_initialized or self.is_muted:
            return False

        print(f"Mock audio playing file: {file_path} (volume: {self.volume:.1f})")

        # Simulate file playback (assume 2 second default duration)
        time.sleep(2.0)
        return True

    def play_sound_effect(self, effect_name: str) -> bool:
        """Play predefined sound effect"""
        if not self.is_initialized or self.is_muted:
            return False

        if effect_name not in self.sound_effects:
            print(f"Unknown sound effect: {effect_name}")
            return False

        duration_map = {
            'beep': 0.2,
            'alert': 0.5,
            'success': 0.3,
            'error': 0.4,
            'notification': 0.3,
            'startup': 1.0
        }

        duration = duration_map.get(effect_name, 0.3)
        print(f"Mock sound effect: '{effect_name}' (volume: {self.volume:.1f}, duration: {duration:.1f}s)")

        time.sleep(duration)
        return True

    def record_audio(self, duration: float = 5.0) -> Optional[np.ndarray]:
        """Record audio for specified duration"""
        if not self.is_initialized:
            return None

        print(f"Mock recording audio for {duration:.1f}s (gain: {self.microphone_gain:.1f})")

        # Generate mock audio data (sine wave with noise)
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)

        # Create a mix of frequencies to simulate speech
        frequency1 = 440  # A note
        frequency2 = 880  # Higher A note

        audio_data = (
            0.3 * np.sin(2 * np.pi * frequency1 * t) +
            0.2 * np.sin(2 * np.pi * frequency2 * t) +
            0.1 * np.random.normal(0, 1, samples)  # Add noise
        )

        # Apply gain
        audio_data *= self.microphone_gain

        # Simulate recording time
        time.sleep(duration)

        self.recorded_data = audio_data
        print("Mock audio recording completed")
        return audio_data

    def start_recording(self) -> bool:
        """Start continuous audio recording"""
        if not self.is_initialized:
            return False

        self.is_recording_flag = True
        self.recording_start_time = time.time()
        print("Mock audio recording started")
        return True

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data"""
        if not self.is_recording_flag:
            return None

        self.is_recording_flag = False
        recording_duration = time.time() - self.recording_start_time if self.recording_start_time else 1.0

        print(f"Mock audio recording stopped (duration: {recording_duration:.1f}s)")

        # Generate mock recorded data
        return self.record_audio(recording_duration)

    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.is_recording_flag

    def set_volume(self, volume: float):
        """Set output volume"""
        self.volume = max(0.0, min(1.0, volume))
        print(f"Mock audio volume set to {self.volume:.1f}")

    def get_volume(self) -> float:
        """Get current output volume"""
        return self.volume

    def set_microphone_gain(self, gain: float):
        """Set microphone input gain"""
        self.microphone_gain = max(0.0, min(1.0, gain))
        print(f"Mock microphone gain set to {self.microphone_gain:.1f}")

    def get_microphone_gain(self) -> float:
        """Get current microphone gain"""
        return self.microphone_gain

    def mute(self):
        """Mute audio output"""
        self.is_muted = True
        print("Mock audio muted")

    def unmute(self):
        """Unmute audio output"""
        self.is_muted = False
        print("Mock audio unmuted")

    def is_muted(self) -> bool:
        """Check if audio is muted"""
        return self.is_muted

    def get_audio_devices(self) -> Dict[str, List[str]]:
        """Get available audio devices"""
        return self.audio_devices.copy()

    def set_audio_device(self, device_type: str, device_name: str) -> bool:
        """Set audio device"""
        if device_type not in ['input', 'output']:
            print(f"Invalid device type: {device_type}")
            return False

        if device_name not in self.audio_devices[device_type]:
            print(f"Device not found: {device_name}")
            return False

        if device_type == 'input':
            self.current_input_device = device_name
        else:
            self.current_output_device = device_name

        print(f"Mock {device_type} device set to: {device_name}")
        return True

    def test_audio(self) -> Dict[str, bool]:
        """Test audio input and output functionality"""
        print("Testing mock audio system...")

        # Test output
        output_test = True
        try:
            self.play_sound_effect('beep')
        except Exception as e:
            print(f"Output test failed: {e}")
            output_test = False

        # Test input
        input_test = True
        try:
            test_data = self.record_audio(0.5)  # Short test recording
            if test_data is None:
                input_test = False
        except Exception as e:
            print(f"Input test failed: {e}")
            input_test = False

        results = {
            'output': output_test,
            'input': input_test,
            'overall': output_test and input_test
        }

        print(f"Mock audio test results: {results}")
        return results

    def is_connected(self) -> bool:
        """Check if audio hardware is connected"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get audio system status and diagnostics"""
        return {
            'connected': self.is_connected(),
            'initialized': self.is_initialized,
            'volume': self.volume,
            'microphone_gain': self.microphone_gain,
            'muted': self.is_muted,
            'recording': self.is_recording_flag,
            'sample_rate': self.sample_rate,
            'devices': {
                'input': self.current_input_device,
                'output': self.current_output_device
            },
            'available_voices': self.voices,
            'available_effects': self.sound_effects,
            'audio_config': self.config
        }

    def demonstrate_audio(self):
        """Demonstrate audio capabilities for testing"""
        print("Starting mock audio demonstration...")

        # Test TTS with different voices
        for voice in self.voices[:3]:  # Test first 3 voices
            self.play_text(f"Hello, this is {voice} voice", voice)

        # Test sound effects
        for effect in ['beep', 'success', 'alert']:
            self.play_sound_effect(effect)

        # Test recording
        print("Testing audio recording (2 seconds)...")
        recorded = self.record_audio(2.0)
        if recorded is not None:
            print(f"Recording successful: {len(recorded)} samples")

        print("Mock audio demonstration completed")

    def shutdown(self):
        """Shutdown audio system"""
        if self.is_recording_flag:
            self.stop_recording()

        self.is_initialized = False
        print("Mock audio system shutdown completed")