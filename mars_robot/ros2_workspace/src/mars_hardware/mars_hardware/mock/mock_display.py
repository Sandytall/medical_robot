"""
Mock Display Implementation for Development
"""
import time
from typing import Dict, Any, Tuple, Optional

from ..interfaces.display_interface import DisplayInterface, EmotionType


class MockDisplay(DisplayInterface):
    """Mock display implementation for emotion and information display"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Display settings
        self.resolution = self.config.get('resolution', [800, 600])
        self.brightness = 0.8
        self.background_color = (0, 0, 0)  # Black background

        # Current display state
        self.current_emotion = EmotionType.NEUTRAL
        self.current_text = ""
        self.current_mode = "idle"

        # Emotion representations for terminal display
        self.emotion_ascii = {
            EmotionType.HAPPY: "😊",
            EmotionType.SAD: "😢",
            EmotionType.ANGRY: "😠",
            EmotionType.SURPRISED: "😲",
            EmotionType.CONFUSED: "😕",
            EmotionType.THINKING: "🤔",
            EmotionType.SLEEPING: "😴",
            EmotionType.EXCITED: "🤗",
            EmotionType.NEUTRAL: "😐"
        }

        self.is_initialized = False

    def initialize(self) -> bool:
        """Initialize display hardware"""
        self.is_initialized = True
        print("Mock display initialized")
        print(f"Display device: {self.config.get('device', 'Mock Display')}")
        print(f"Resolution: {self.resolution[0]}x{self.resolution[1]}")
        self.clear_display()
        return True

    def show_emotion(self, emotion: EmotionType, duration: float = 0.0):
        """Display emotion"""
        if not self.is_initialized:
            return

        self.current_emotion = emotion
        emotion_symbol = self.emotion_ascii.get(emotion, "😐")

        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - EMOTION: {emotion.value.upper()}")
        print(f"{'='*50}")
        print(f"          {emotion_symbol}  {emotion_symbol}  {emotion_symbol}")
        print(f"        {emotion_symbol}      {emotion_symbol}      {emotion_symbol}")
        print(f"          {emotion_symbol}  {emotion_symbol}  {emotion_symbol}")
        print(f"{'='*50}")

        if duration > 0:
            print(f"[Emotion displayed for {duration:.1f}s]")
            time.sleep(duration)
            self.show_emotion(EmotionType.NEUTRAL)

    def show_text(self, text: str, font_size: int = 24, color: Tuple[int, int, int] = (255, 255, 255)):
        """Display text message"""
        if not self.is_initialized:
            return

        self.current_text = text

        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - TEXT MESSAGE")
        print(f"{'='*50}")
        print(f"Font Size: {font_size}px | Color: RGB{color}")
        print(f"\n{text.center(48)}\n")
        print(f"{'='*50}")

    def show_status(self, status: str, level: str = "info"):
        """Show status message"""
        level_symbols = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅'
        }

        symbol = level_symbols.get(level, 'ℹ️')

        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - STATUS [{level.upper()}]")
        print(f"{'='*50}")
        print(f"{symbol} {status}")
        print(f"{'='*50}")

    def show_progress(self, progress: float, message: str = ""):
        """Show progress indicator"""
        progress = max(0.0, min(1.0, progress))
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - PROGRESS")
        print(f"{'='*50}")
        if message:
            print(f"{message}")
        print(f"[{bar}] {progress*100:.1f}%")
        print(f"{'='*50}")

    def show_patient_info(self, name: str, patient_id: str, status: str = ""):
        """Display patient information"""
        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - PATIENT INFO")
        print(f"{'='*50}")
        print(f"Name: {name}")
        print(f"Patient ID: {patient_id}")
        if status:
            print(f"Status: {status}")
        print(f"{'='*50}")

    def show_medication_reminder(self, patient_name: str, medication: str, time: str):
        """Display medication reminder"""
        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - MEDICATION REMINDER")
        print(f"{'='*50}")
        print(f"🕐 MEDICATION TIME 🕐")
        print(f"Patient: {patient_name}")
        print(f"Medication: {medication}")
        print(f"Time: {time}")
        print(f"{'='*50}")

    def show_question_mode(self):
        """Display question/listening mode interface"""
        self.current_mode = "question"
        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - QUESTION MODE")
        print(f"{'='*50}")
        print(f"🎤 I'm listening... Ask me a question!")
        print(f"{'='*50}")

    def show_follow_mode(self, target_name: str = ""):
        """Display follow mode interface"""
        self.current_mode = "follow"
        target_text = f" - Following {target_name}" if target_name else ""

        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - FOLLOW MODE")
        print(f"{'='*50}")
        print(f"👁️ Following Mode Active{target_text}")
        print(f"🚶‍♀️➡️🤖 Stay in front of me!")
        print(f"{'='*50}")

    def show_manual_mode(self):
        """Display manual control mode interface"""
        self.current_mode = "manual"
        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - MANUAL MODE")
        print(f"{'='*50}")
        print(f"🎮 Manual Control Active")
        print(f"Use gamepad to control movement")
        print(f"{'='*50}")

    def show_idle_mode(self):
        """Display idle mode interface"""
        self.current_mode = "idle"
        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - IDLE MODE")
        print(f"{'='*50}")
        print(f"💤 MARS is in idle mode")
        print(f"Say 'Hey Mars' to activate!")
        print(f"{'='*50}")

    def clear_display(self):
        """Clear the display"""
        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - CLEARED")
        print(f"{'='*50}")
        print(f"{'   ' * 16}")
        print(f"{'   ' * 16}")
        print(f"{'   ' * 16}")
        print(f"{'='*50}")

        self.current_text = ""
        self.current_emotion = EmotionType.NEUTRAL

    def set_brightness(self, brightness: float):
        """Set display brightness"""
        self.brightness = max(0.0, min(1.0, brightness))
        print(f"Mock display brightness set to {self.brightness:.1f}")

    def get_brightness(self) -> float:
        """Get current brightness level"""
        return self.brightness

    def set_background_color(self, color: Tuple[int, int, int]):
        """Set background color"""
        self.background_color = color
        print(f"Mock display background color set to RGB{color}")

    def animate_emotion(self, emotion: EmotionType, animation_type: str = "pulse"):
        """Display animated emotion"""
        print(f"Mock display animating emotion: {emotion.value} ({animation_type})")

        emotion_symbol = self.emotion_ascii.get(emotion, "😐")

        if animation_type == "pulse":
            for i in range(3):
                print(f"  {emotion_symbol} ", end="", flush=True)
                time.sleep(0.3)
                print(f"\b\b\b{emotion_symbol*2} ", end="", flush=True)
                time.sleep(0.3)
                print(f"\b\b\b{emotion_symbol*3} ", end="", flush=True)
                time.sleep(0.3)
                print(f"\b\b\b{emotion_symbol} ", end="", flush=True)
                time.sleep(0.3)

        elif animation_type == "blink":
            for i in range(5):
                print(f"  {emotion_symbol} ", end="", flush=True)
                time.sleep(0.2)
                print(f"\b\b\b   ", end="", flush=True)
                time.sleep(0.2)

        elif animation_type == "fade":
            fade_levels = ["░", "▒", "▓", "█", "▓", "▒", "░"]
            for level in fade_levels:
                print(f"  {level}{emotion_symbol}{level} ", end="", flush=True)
                time.sleep(0.2)

        print()  # New line after animation

    def show_custom_image(self, image_path: str):
        """Display custom image from file"""
        print(f"\n{'='*50}")
        print(f"MARS DISPLAY - CUSTOM IMAGE")
        print(f"{'='*50}")
        print(f"📷 Displaying: {image_path}")
        print(f"[Image would be shown on real display]")
        print(f"{'='*50}")

    def get_display_resolution(self) -> Tuple[int, int]:
        """Get display resolution"""
        return tuple(self.resolution)

    def is_connected(self) -> bool:
        """Check if display is connected"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get display status and diagnostics"""
        return {
            'connected': self.is_connected(),
            'initialized': self.is_initialized,
            'resolution': self.resolution,
            'brightness': self.brightness,
            'background_color': self.background_color,
            'current_state': {
                'emotion': self.current_emotion.value,
                'text': self.current_text,
                'mode': self.current_mode
            },
            'display_config': self.config
        }

    def demonstrate_display(self):
        """Demonstrate display capabilities for testing"""
        print("Starting mock display demonstration...")

        # Test emotions
        emotions_to_test = [
            EmotionType.HAPPY,
            EmotionType.SAD,
            EmotionType.EXCITED,
            EmotionType.THINKING,
            EmotionType.NEUTRAL
        ]

        for emotion in emotions_to_test:
            self.show_emotion(emotion, 1.0)

        # Test different display modes
        modes = [
            ("idle", self.show_idle_mode),
            ("manual", self.show_manual_mode),
            ("follow", lambda: self.show_follow_mode("Patient John")),
            ("question", self.show_question_mode)
        ]

        for mode_name, mode_func in modes:
            print(f"\nTesting {mode_name} mode...")
            mode_func()
            time.sleep(1)

        # Test animations
        print("\nTesting animations...")
        self.animate_emotion(EmotionType.HAPPY, "pulse")
        self.animate_emotion(EmotionType.EXCITED, "blink")

        self.clear_display()
        print("Mock display demonstration completed")

    def shutdown(self):
        """Shutdown display"""
        self.clear_display()
        self.is_initialized = False
        print("Mock display shutdown completed")