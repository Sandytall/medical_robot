"""
Display Overlay Interface for Mars Robot
Manages the visual display overlay with eyes, camera feed, status, and animations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import numpy as np


class EyeEmotion(Enum):
    """Eye emotion states"""
    SLEEPY = 0
    NORMAL = 1
    CLOSED = 2
    LOOKING_LEFT = 3
    SQUINTING = 4
    LOOKING_RIGHT = 5
    LOVE = 6


class EyePosition(Enum):
    """Eye position states"""
    LEFT = 0
    CENTER = 1
    RIGHT = 2


class DisplayMode(Enum):
    """Display mode states"""
    IDLE_EYES = "idle_eyes"
    CAMERA_FEED = "camera_feed"
    STATUS_DISPLAY = "status_display"
    ERROR_DISPLAY = "error_display"
    MODE_DISPLAY = "mode_display"


class DisplayOverlayInterface(ABC):
    """Abstract interface for display overlay system"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the display overlay system"""
        pass

    @abstractmethod
    def update_display_mode(self, mode: DisplayMode):
        """Update the current display mode"""
        pass

    @abstractmethod
    def show_camera_feed(self, camera_frame: np.ndarray):
        """Display camera feed overlay"""
        pass

    @abstractmethod
    def show_robot_mode(self, mode: str, ready: bool = False):
        """Display current robot mode and ready status"""
        pass

    @abstractmethod
    def show_error(self, error_message: str, error_type: str = "warning"):
        """Display error message overlay"""
        pass

    @abstractmethod
    def show_idle_eyes(self, emotion: EyeEmotion = EyeEmotion.NORMAL,
                      position: EyePosition = EyePosition.CENTER):
        """Display animated eyes when in idle mode"""
        pass

    @abstractmethod
    def animate_eye_transition(self, from_emotion: EyeEmotion,
                              to_emotion: EyeEmotion, duration: float = 0.5):
        """Smooth animation between eye emotions"""
        pass

    @abstractmethod
    def set_eye_emotion(self, emotion: EyeEmotion):
        """Set current eye emotion"""
        pass

    @abstractmethod
    def set_eye_position(self, position: EyePosition):
        """Set current eye position"""
        pass

    @abstractmethod
    def blink_eyes(self, duration: float = 0.15):
        """Perform blinking animation"""
        pass

    @abstractmethod
    def clear_overlay(self):
        """Clear all overlay content"""
        pass

    @abstractmethod
    def set_overlay_transparency(self, alpha: float):
        """Set overlay transparency (0.0-1.0)"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get display overlay status"""
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown the display overlay system"""
        pass