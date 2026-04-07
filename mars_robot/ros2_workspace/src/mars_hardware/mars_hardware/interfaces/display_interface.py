"""
Display Interface for Emotion and Information Display
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
from enum import Enum


class EmotionType(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    CONFUSED = "confused"
    THINKING = "thinking"
    SLEEPING = "sleeping"
    EXCITED = "excited"
    NEUTRAL = "neutral"


class DisplayInterface(ABC):
    """Abstract interface for display operations"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize display hardware"""
        pass

    @abstractmethod
    def show_emotion(self, emotion: EmotionType, duration: float = 0.0):
        """
        Display emotion
        Args:
            emotion: Emotion type to display
            duration: How long to show (0 = permanent)
        """
        pass

    @abstractmethod
    def show_text(self, text: str, font_size: int = 24, color: Tuple[int, int, int] = (255, 255, 255)):
        """
        Display text message
        Args:
            text: Text to display
            font_size: Font size in pixels
            color: RGB color tuple
        """
        pass

    @abstractmethod
    def show_status(self, status: str, level: str = "info"):
        """
        Show status message
        Args:
            status: Status text
            level: 'info', 'warning', 'error', 'success'
        """
        pass

    @abstractmethod
    def show_progress(self, progress: float, message: str = ""):
        """
        Show progress indicator
        Args:
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
        """
        pass

    @abstractmethod
    def show_patient_info(self, name: str, patient_id: str, status: str = ""):
        """
        Display patient information
        Args:
            name: Patient name
            patient_id: Patient ID
            status: Optional status message
        """
        pass

    @abstractmethod
    def show_medication_reminder(self, patient_name: str, medication: str, time: str):
        """
        Display medication reminder
        Args:
            patient_name: Name of patient
            medication: Medication name
            time: Time for medication
        """
        pass

    @abstractmethod
    def show_question_mode(self):
        """Display question/listening mode interface"""
        pass

    @abstractmethod
    def show_follow_mode(self, target_name: str = ""):
        """
        Display follow mode interface
        Args:
            target_name: Name of person being followed
        """
        pass

    @abstractmethod
    def show_manual_mode(self):
        """Display manual control mode interface"""
        pass

    @abstractmethod
    def show_idle_mode(self):
        """Display idle mode interface"""
        pass

    @abstractmethod
    def clear_display(self):
        """Clear the display"""
        pass

    @abstractmethod
    def set_brightness(self, brightness: float):
        """
        Set display brightness
        Args:
            brightness: Brightness level (0.0 to 1.0)
        """
        pass

    @abstractmethod
    def get_brightness(self) -> float:
        """Get current brightness level"""
        pass

    @abstractmethod
    def set_background_color(self, color: Tuple[int, int, int]):
        """
        Set background color
        Args:
            color: RGB color tuple
        """
        pass

    @abstractmethod
    def animate_emotion(self, emotion: EmotionType, animation_type: str = "pulse"):
        """
        Display animated emotion
        Args:
            emotion: Emotion to animate
            animation_type: Animation style ('pulse', 'fade', 'blink')
        """
        pass

    @abstractmethod
    def show_custom_image(self, image_path: str):
        """Display custom image from file"""
        pass

    @abstractmethod
    def get_display_resolution(self) -> Tuple[int, int]:
        """Get display resolution as (width, height)"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if display is connected"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get display status and diagnostics"""
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown display and release resources"""
        pass