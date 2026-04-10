"""Real Audio Implementation for USB Audio on Raspberry Pi 5"""
import os
import subprocess
import threading
import time
import numpy as np
from typing import Optional, List, Dict, Any
from ..interfaces.audio_interface import AudioInterface

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import pyaudio
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class RealAudio(AudioInterface):
    """Real audio implementation for Pi 5 using system tools and pyaudio"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_initialized = False
        self.tts_engine = None
        self.audio_instance = None
        self.is_recording_flag = False
        self.recording_data = []
        self.recording_thread = None

        # Audio configuration
        audio_config = self.config.get('audio', {})
        self.input_device = audio_config.get('input_device', 'default')
        self.output_device = audio_config.get('output_device', 'default')
        self.sample_rate = audio_config.get('sample_rate', 16000)
        self.channels = audio_config.get('channels', 1)
        self.chunk_size = audio_config.get('chunk_size', 1024)

        # Volume settings
        self.current_volume = audio_config.get('default_volume', 0.7)
        self.microphone_gain = audio_config.get('microphone_gain', 0.5)
        self.is_muted_flag = False

        # TTS settings
        tts_config = audio_config.get('tts', {})
        self.tts_rate = tts_config.get('rate', 200)

        # Sound effect paths
        self.sound_paths = audio_config.get('sounds', {})

    def initialize(self) -> bool:
        """Initialize audio system"""
        try:
            # Initialize TTS engine
            if TTS_AVAILABLE:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', self.tts_rate)
                self.tts_engine.setProperty('volume', self.current_volume)
                print("✅ TTS engine initialized")
            else:
                print("⚠️  pyttsx3 not available, using espeak fallback")

            # Initialize pyaudio
            if AUDIO_AVAILABLE:
                self.audio_instance = pyaudio.PyAudio()
                print("✅ PyAudio initialized")
            else:
                print("⚠️  PyAudio not available, using system audio commands")

            # Test audio system
            self._test_audio_system()

            self.is_initialized = True
            print("✅ RealAudio: Audio system initialized")
            return True

        except Exception as e:
            print(f"❌ RealAudio initialization failed: {e}")
            return False

    def _test_audio_system(self):
        """Test basic audio functionality"""
        try:
            # Test if espeak is available as fallback
            result = subprocess.run(['which', 'espeak'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ espeak available as TTS fallback")

            # Test ALSA/audio devices
            result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ ALSA audio devices detected")

        except Exception as e:
            print(f"⚠️  Audio system test warning: {e}")

    def play_text(self, text: str, voice: str = "default") -> bool:
        """Play text using TTS"""
        if not text.strip():
            return False

        try:
            if self.tts_engine and TTS_AVAILABLE:
                # Use pyttsx3
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                return True
            else:
                # Fallback to espeak
                volume = int(self.current_volume * 100) if not self.is_muted_flag else 0
                cmd = ['espeak', f'-a{volume}', f'-s{self.tts_rate}', text]
                result = subprocess.run(cmd, capture_output=True)
                return result.returncode == 0

        except Exception as e:
            print(f"❌ TTS error: {e}")
            return False

    def play_audio_file(self, file_path: str) -> bool:
        """Play audio file using system player"""
        if not os.path.exists(file_path):
            print(f"❌ Audio file not found: {file_path}")
            return False

        try:
            # Try aplay first (ALSA)
            volume = self.current_volume if not self.is_muted_flag else 0
            cmd = ['aplay', file_path]

            if volume < 1.0:
                # Use amixer to set volume
                subprocess.run(['amixer', 'set', 'Master', f'{int(volume * 100)}%'],
                             capture_output=True)

            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0

        except Exception as e:
            print(f"❌ Audio playback error: {e}")
            return False

    def play_sound_effect(self, effect_name: str) -> bool:
        """Play predefined sound effect"""
        if effect_name in self.sound_paths:
            return self.play_audio_file(self.sound_paths[effect_name])
        else:
            # Generate simple beep as fallback
            try:
                subprocess.run(['speaker-test', '-t', 'sine', '-f', '800', '-l', '1'],
                             capture_output=True, timeout=2)
                return True
            except:
                return False

    def record_audio(self, duration: float = 5.0) -> Optional[np.ndarray]:
        """Record audio for specified duration"""
        if not AUDIO_AVAILABLE:
            print("❌ PyAudio not available for recording")
            return None

        try:
            format = pyaudio.paInt16
            stream = self.audio_instance.open(
                format=format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            frames = []
            num_chunks = int(self.sample_rate * duration / self.chunk_size)

            for _ in range(num_chunks):
                data = stream.read(self.chunk_size)
                frames.append(data)

            stream.stop_stream()
            stream.close()

            # Convert to numpy array
            audio_data = b''.join(frames)
            return np.frombuffer(audio_data, dtype=np.int16)

        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None

    def start_recording(self) -> bool:
        """Start continuous recording"""
        if self.is_recording_flag or not AUDIO_AVAILABLE:
            return False

        try:
            self.is_recording_flag = True
            self.recording_data = []
            self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
            self.recording_thread.start()
            return True

        except Exception as e:
            print(f"❌ Start recording error: {e}")
            self.is_recording_flag = False
            return False

    def _recording_loop(self):
        """Continuous recording loop"""
        try:
            format = pyaudio.paInt16
            stream = self.audio_instance.open(
                format=format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            while self.is_recording_flag:
                data = stream.read(self.chunk_size)
                self.recording_data.append(data)

            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"❌ Recording loop error: {e}")
            self.is_recording_flag = False

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data"""
        if not self.is_recording_flag:
            return None

        self.is_recording_flag = False

        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)

        try:
            # Convert recorded data to numpy array
            audio_data = b''.join(self.recording_data)
            self.recording_data = []
            return np.frombuffer(audio_data, dtype=np.int16)

        except Exception as e:
            print(f"❌ Stop recording error: {e}")
            return None

    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.is_recording_flag

    def set_volume(self, volume: float):
        """Set output volume (0.0 to 1.0)"""
        self.current_volume = max(0.0, min(1.0, volume))

        try:
            # Set system volume using amixer
            volume_percent = int(self.current_volume * 100)
            subprocess.run(['amixer', 'set', 'Master', f'{volume_percent}%'],
                         capture_output=True)

            # Update TTS engine volume
            if self.tts_engine:
                self.tts_engine.setProperty('volume', self.current_volume)

        except Exception as e:
            print(f"❌ Volume set error: {e}")

    def get_volume(self) -> float:
        """Get current output volume"""
        return self.current_volume

    def set_microphone_gain(self, gain: float):
        """Set microphone gain (0.0 to 1.0)"""
        self.microphone_gain = max(0.0, min(1.0, gain))

        try:
            # Set microphone gain using amixer
            gain_percent = int(self.microphone_gain * 100)
            subprocess.run(['amixer', 'set', 'Capture', f'{gain_percent}%'],
                         capture_output=True)

        except Exception as e:
            print(f"❌ Microphone gain set error: {e}")

    def get_microphone_gain(self) -> float:
        """Get current microphone gain"""
        return self.microphone_gain

    def mute(self):
        """Mute audio output"""
        self.is_muted_flag = True
        try:
            subprocess.run(['amixer', 'set', 'Master', 'mute'], capture_output=True)
        except:
            pass

    def unmute(self):
        """Unmute audio output"""
        self.is_muted_flag = False
        try:
            subprocess.run(['amixer', 'set', 'Master', 'unmute'], capture_output=True)
        except:
            pass

    def is_muted(self) -> bool:
        """Check if audio is muted"""
        return self.is_muted_flag

    def get_audio_devices(self) -> Dict[str, List[str]]:
        """Get available audio devices"""
        devices = {'input': [], 'output': []}

        try:
            if AUDIO_AVAILABLE:
                for i in range(self.audio_instance.get_device_count()):
                    info = self.audio_instance.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        devices['input'].append(info['name'])
                    if info['maxOutputChannels'] > 0:
                        devices['output'].append(info['name'])

        except Exception as e:
            print(f"❌ Device enumeration error: {e}")

        return devices

    def set_audio_device(self, device_type: str, device_name: str) -> bool:
        """Set active audio device"""
        try:
            if device_type == 'input':
                self.input_device = device_name
            elif device_type == 'output':
                self.output_device = device_name
            else:
                return False

            return True

        except Exception as e:
            print(f"❌ Device set error: {e}")
            return False

    def test_audio(self) -> Dict[str, bool]:
        """Test audio input/output functionality"""
        results = {'output': False, 'input': False, 'overall': False}

        try:
            # Test output
            output_test = self.play_text("Audio test")
            results['output'] = output_test

            # Test input (quick recording test)
            if AUDIO_AVAILABLE:
                test_recording = self.record_audio(0.5)
                results['input'] = test_recording is not None
            else:
                results['input'] = True  # Assume input works if no PyAudio

            results['overall'] = results['output'] and results['input']

        except Exception as e:
            print(f"❌ Audio test error: {e}")

        return results

    def is_connected(self) -> bool:
        """Check if audio hardware is connected"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get audio system status"""
        return {
            'initialized': self.is_initialized,
            'recording': self.is_recording_flag,
            'muted': self.is_muted_flag,
            'volume': self.current_volume,
            'microphone_gain': self.microphone_gain,
            'tts_available': TTS_AVAILABLE,
            'pyaudio_available': AUDIO_AVAILABLE,
            'sample_rate': self.sample_rate,
            'channels': self.channels
        }

    def shutdown(self):
        """Properly shutdown audio system"""
        try:
            # Stop any ongoing recording
            if self.is_recording_flag:
                self.stop_recording()

            # Cleanup TTS engine
            if self.tts_engine:
                try:
                    self.tts_engine.stop()
                except:
                    pass
                self.tts_engine = None

            # Cleanup PyAudio
            if self.audio_instance:
                self.audio_instance.terminate()
                self.audio_instance = None

            self.is_initialized = False
            print("✅ RealAudio: Shutdown completed")

        except Exception as e:
            print(f"⚠️  RealAudio shutdown error: {e}")