"""
Audio Interface for Sound Input/Output
"""
from abc import ABC, abstractmethod
import numpy as np
from typing import Optional, List, Dict, Any


class AudioInterface(ABC):
    """Abstract interface for audio operations"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize audio hardware"""
        pass

    @abstractmethod
    def play_text(self, text: str, voice: str = "default") -> bool:
        """
        Convert text to speech and play
        Args:
            text: Text to speak
            voice: Voice type (default, male, female, etc.)
        """
        pass

    @abstractmethod
    def play_audio_file(self, file_path: str) -> bool:
        """Play audio file"""
        pass

    @abstractmethod
    def play_sound_effect(self, effect_name: str) -> bool:
        """
        Play predefined sound effect
        Args:
            effect_name: Name of sound effect (beep, alert, success, etc.)
        """
        pass

    @abstractmethod
    def record_audio(self, duration: float = 5.0) -> Optional[np.ndarray]:
        """
        Record audio for specified duration
        Args:
            duration: Recording duration in seconds
        Returns:
            Audio data as numpy array or None if failed
        """
        pass

    @abstractmethod
    def start_recording(self) -> bool:
        """Start continuous audio recording"""
        pass

    @abstractmethod
    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data"""
        pass

    @abstractmethod
    def is_recording(self) -> bool:
        """Check if currently recording"""
        pass

    @abstractmethod
    def set_volume(self, volume: float):
        """
        Set output volume
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        pass

    @abstractmethod
    def get_volume(self) -> float:
        """Get current output volume"""
        pass

    @abstractmethod
    def set_microphone_gain(self, gain: float):
        """
        Set microphone input gain
        Args:
            gain: Gain level (0.0 to 1.0)
        """
        pass

    @abstractmethod
    def get_microphone_gain(self) -> float:
        """Get current microphone gain"""
        pass

    @abstractmethod
    def mute(self):
        """Mute audio output"""
        pass

    @abstractmethod
    def unmute(self):
        """Unmute audio output"""
        pass

    @abstractmethod
    def is_muted(self) -> bool:
        """Check if audio is muted"""
        pass

    @abstractmethod
    def get_audio_devices(self) -> Dict[str, List[str]]:
        """Get available audio devices as {'input': [...], 'output': [...]}"""
        pass

    @abstractmethod
    def set_audio_device(self, device_type: str, device_name: str) -> bool:
        """
        Set audio device
        Args:
            device_type: 'input' or 'output'
            device_name: Name of the device
        """
        pass

    @abstractmethod
    def test_audio(self) -> Dict[str, bool]:
        """Test audio input and output functionality"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if audio hardware is connected"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get audio system status and diagnostics"""
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown audio system and release resources"""
        pass