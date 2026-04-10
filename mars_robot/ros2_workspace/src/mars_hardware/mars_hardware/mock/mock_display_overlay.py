"""
Mock Display Overlay Implementation for Mars Robot
Testing implementation for development without display hardware
"""
import time
import threading
from typing import Dict, Any, Optional
import numpy as np

from ..interfaces.display_overlay_interface import (
    DisplayOverlayInterface, EyeEmotion, EyePosition, DisplayMode
)


class MockDisplayOverlay(DisplayOverlayInterface):
    """Mock display overlay implementation for testing"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_initialized = False

        # Display settings
        display_config = self.config.get('display', {})
        self.screen_width = display_config.get('resolution', [800, 600])[0]
        self.screen_height = display_config.get('resolution', [800, 600])[1]

        # State tracking
        self.current_display_mode = DisplayMode.IDLE_EYES
        self.current_emotion = EyeEmotion.NORMAL
        self.current_position = EyePosition.CENTER
        self.overlay_alpha = 0.9

        # Animation state
        self.is_animating = False
        self.animation_start_time = 0
        self.animation_duration = 0.5

        # Content state
        self.current_camera_frame = None
        self.current_robot_mode = "idle"
        self.robot_ready = False
        self.error_text = ""
        self.status_text = ""
        self.mode_text = ""

        print("🎭 MockDisplayOverlay: Initialized for testing")

    def initialize(self) -> bool:
        """Initialize the mock display overlay system"""
        try:
            self.is_initialized = True
            print("✅ MockDisplayOverlay: Initialized successfully")
            return True

        except Exception as e:
            print(f"❌ MockDisplayOverlay initialization failed: {e}")
            return False

    def update_display_mode(self, mode: DisplayMode):
        """Update the current display mode"""
        self.current_display_mode = mode
        print(f"🎭 MockDisplayOverlay: Display mode changed to {mode.value}")

    def show_camera_feed(self, camera_frame: np.ndarray):
        """Display camera feed overlay"""
        self.current_camera_frame = camera_frame.copy() if camera_frame is not None else None
        self.current_display_mode = DisplayMode.CAMERA_FEED

        if camera_frame is not None:
            height, width = camera_frame.shape[:2]
            print(f"📷 MockDisplayOverlay: Showing camera feed ({width}x{height})")
        else:
            print("📷 MockDisplayOverlay: Camera feed cleared")

    def show_robot_mode(self, mode: str, ready: bool = False):
        """Display current robot mode and ready status"""
        self.current_robot_mode = mode
        self.robot_ready = ready
        self.mode_text = f"Mode: {mode}"
        self.current_display_mode = DisplayMode.MODE_DISPLAY

        ready_status = "READY" if ready else "NOT READY"
        print(f"🤖 MockDisplayOverlay: Mode={mode}, Status={ready_status}")

    def show_error(self, error_message: str, error_type: str = "warning"):
        """Display error message overlay"""
        self.error_text = f"{error_type.upper()}: {error_message}"
        self.current_display_mode = DisplayMode.ERROR_DISPLAY
        print(f"❌ MockDisplayOverlay: Error - {error_type}: {error_message}")

    def show_idle_eyes(self, emotion: EyeEmotion = EyeEmotion.NORMAL,
                      position: EyePosition = EyePosition.CENTER):
        """Display animated eyes when in idle mode"""
        self.current_display_mode = DisplayMode.IDLE_EYES
        self.set_eye_emotion(emotion)
        self.set_eye_position(position)
        print(f"👀 MockDisplayOverlay: Showing idle eyes - {emotion.name}, {position.name}")

    def animate_eye_transition(self, from_emotion: EyeEmotion,
                              to_emotion: EyeEmotion, duration: float = 0.5):
        """Smooth animation between eye emotions"""
        self.is_animating = True
        self.animation_start_time = time.time()
        self.animation_duration = duration

        print(f"🎬 MockDisplayOverlay: Animating {from_emotion.name} → {to_emotion.name} ({duration}s)")

        # Simulate animation in separate thread
        def complete_animation():
            time.sleep(duration)
            self.current_emotion = to_emotion
            self.is_animating = False
            print(f"✨ MockDisplayOverlay: Animation complete - now {to_emotion.name}")

        threading.Thread(target=complete_animation, daemon=True).start()

    def set_eye_emotion(self, emotion: EyeEmotion):
        """Set current eye emotion"""
        if not self.is_animating:
            old_emotion = self.current_emotion
            self.current_emotion = emotion
            if old_emotion != emotion:
                print(f"😊 MockDisplayOverlay: Eye emotion changed to {emotion.name}")

    def set_eye_position(self, position: EyePosition):
        """Set current eye position"""
        if not self.is_animating:
            old_position = self.current_position
            self.current_position = position
            if old_position != position:
                print(f"👁️ MockDisplayOverlay: Eye position changed to {position.name}")

    def blink_eyes(self, duration: float = 0.15):
        """Perform blinking animation"""
        if not self.is_animating:
            print(f"😉 MockDisplayOverlay: Blinking for {duration}s")
            current_emotion = self.current_emotion
            self.animate_eye_transition(current_emotion, EyeEmotion.CLOSED, duration / 2)

            # Schedule eye opening
            def open_eyes():
                time.sleep(duration)
                self.animate_eye_transition(EyeEmotion.CLOSED, current_emotion, duration / 2)

            threading.Thread(target=open_eyes, daemon=True).start()

    def clear_overlay(self):
        """Clear all overlay content"""
        self.current_display_mode = DisplayMode.IDLE_EYES
        self.current_camera_frame = None
        self.error_text = ""
        self.status_text = ""
        self.mode_text = ""
        print("🧹 MockDisplayOverlay: Overlay cleared - returning to idle eyes")

    def set_overlay_transparency(self, alpha: float):
        """Set overlay transparency (0.0-1.0)"""
        self.overlay_alpha = max(0.0, min(1.0, alpha))
        print(f"🔳 MockDisplayOverlay: Transparency set to {alpha:.2f}")

    def get_status(self) -> Dict[str, Any]:
        """Get display overlay status"""
        return {
            'initialized': self.is_initialized,
            'mock_mode': True,
            'current_mode': self.current_display_mode.value,
            'current_emotion': self.current_emotion.value,
            'current_position': self.current_position.value,
            'is_animating': self.is_animating,
            'screen_resolution': [self.screen_width, self.screen_height],
            'overlay_alpha': self.overlay_alpha,
            'robot_ready': self.robot_ready,
            'current_robot_mode': self.current_robot_mode
        }

    def shutdown(self):
        """Shutdown the display overlay system"""
        self.is_initialized = False
        self.current_display_mode = DisplayMode.IDLE_EYES
        print("✅ MockDisplayOverlay: Shutdown completed")