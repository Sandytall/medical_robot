"""
Display Overlay Service for Mars Robot
Manages the display overlay system and integrates with robot state
"""
import time
import threading
from typing import Dict, Any, Optional
from enum import Enum
import numpy as np

from ..interfaces.display_overlay_interface import (
    DisplayOverlayInterface, EyeEmotion, EyePosition, DisplayMode
)


class RobotState(Enum):
    """Robot state for display overlay"""
    STARTING_UP = "starting_up"
    IDLE = "idle"
    MANUAL = "manual"
    FOLLOW = "follow"
    REGISTRATION = "registration"
    QUESTION = "question"
    MEDICINE = "medicine"
    HEALTH_CHECK = "health_check"
    ERROR = "error"
    EMERGENCY = "emergency"


class DisplayOverlayService:
    """Service that manages display overlay based on robot state"""

    def __init__(self, display_overlay: DisplayOverlayInterface, config: Dict[str, Any] = None):
        self.display_overlay = display_overlay
        self.config = config or {}

        # State tracking
        self.current_robot_state = RobotState.STARTING_UP
        self.robot_ready = False
        self.is_camera_active = False
        self.current_error = None
        self.current_camera_frame = None

        # Animation settings
        self.emotion_timer = 0
        self.emotion_interval = 8.0  # Change emotion every 8 seconds in idle
        self.last_emotion_change = time.time()

        # Eye behavior patterns
        self.idle_emotions = [
            EyeEmotion.NORMAL,
            EyeEmotion.SLEEPY,
            EyeEmotion.SQUINTING
        ]
        self.current_idle_emotion_index = 0

        # Threading
        self.service_thread = None
        self.running = False
        self.thread_lock = threading.Lock()

        # Display update frequency
        self.update_frequency = 30  # 30 FPS

    def initialize(self) -> bool:
        """Initialize the display overlay service"""
        try:
            # Initialize display overlay
            if not self.display_overlay.initialize():
                return False

            # Start service thread
            self.running = True
            self.service_thread = threading.Thread(target=self._service_loop, daemon=True)
            self.service_thread.start()

            print("✅ DisplayOverlayService: Initialized successfully")
            return True

        except Exception as e:
            print(f"❌ DisplayOverlayService initialization failed: {e}")
            return False

    def _service_loop(self):
        """Main service loop for display updates"""
        while self.running:
            try:
                with self.thread_lock:
                    # Update display based on current state
                    self._update_display_content()

                    # Handle idle animations
                    if self.current_robot_state == RobotState.IDLE:
                        self._handle_idle_animations()

                time.sleep(1.0 / self.update_frequency)

            except Exception as e:
                print(f"❌ Display overlay service loop error: {e}")
                time.sleep(0.1)

    def _update_display_content(self):
        """Update display content based on current robot state"""
        try:
            if self.current_robot_state == RobotState.STARTING_UP:
                self._show_startup_screen()

            elif self.current_robot_state == RobotState.ERROR:
                self._show_error_screen()

            elif self.current_robot_state == RobotState.EMERGENCY:
                self._show_emergency_screen()

            elif self.is_camera_active and self.current_camera_frame is not None:
                self._show_camera_feed()

            elif self.current_robot_state == RobotState.IDLE:
                self._show_idle_eyes()

            else:
                self._show_mode_display()

        except Exception as e:
            print(f"❌ Display content update error: {e}")

    def _show_startup_screen(self):
        """Show startup screen"""
        self.display_overlay.show_robot_mode("Starting Up...", self.robot_ready)

    def _show_error_screen(self):
        """Show error screen"""
        if self.current_error:
            self.display_overlay.show_error(self.current_error, "error")
        else:
            self.display_overlay.show_error("System Error", "error")

    def _show_emergency_screen(self):
        """Show emergency stop screen"""
        self.display_overlay.show_error("EMERGENCY STOP ACTIVATED", "emergency")

    def _show_camera_feed(self):
        """Show camera feed overlay"""
        if self.current_camera_frame is not None:
            self.display_overlay.show_camera_feed(self.current_camera_frame)

    def _show_idle_eyes(self):
        """Show animated idle eyes"""
        # Get current emotion for idle state
        emotion = self._get_current_idle_emotion()
        position = self._get_current_eye_position()

        self.display_overlay.show_idle_eyes(emotion, position)

    def _show_mode_display(self):
        """Show current robot mode"""
        mode_name = self._get_friendly_mode_name()
        self.display_overlay.show_robot_mode(mode_name, self.robot_ready)

    def _handle_idle_animations(self):
        """Handle idle state animations and emotion changes"""
        current_time = time.time()

        # Change emotions periodically
        if current_time - self.last_emotion_change > self.emotion_interval:
            self._cycle_idle_emotion()
            self.last_emotion_change = current_time

        # Occasional blinking
        if np.random.random() < 0.02:  # 2% chance per frame at 30fps = ~1 blink every 1.67 seconds
            self.display_overlay.blink_eyes(0.2)

    def _cycle_idle_emotion(self):
        """Cycle through different idle emotions"""
        try:
            # Get current and next emotions
            current_emotion = self.idle_emotions[self.current_idle_emotion_index]
            self.current_idle_emotion_index = (self.current_idle_emotion_index + 1) % len(self.idle_emotions)
            next_emotion = self.idle_emotions[self.current_idle_emotion_index]

            # Animate transition
            self.display_overlay.animate_eye_transition(current_emotion, next_emotion, 1.0)

            print(f"👀 Display: Eye emotion cycling {current_emotion.name} → {next_emotion.name}")

        except Exception as e:
            print(f"❌ Emotion cycling error: {e}")

    def _get_current_idle_emotion(self) -> EyeEmotion:
        """Get current idle emotion"""
        try:
            return self.idle_emotions[self.current_idle_emotion_index]
        except:
            return EyeEmotion.NORMAL

    def _get_current_eye_position(self) -> EyePosition:
        """Get current eye position (can be random for idle movement)"""
        # Add some subtle random movement
        if np.random.random() < 0.1:  # 10% chance to look around
            positions = [EyePosition.LEFT, EyePosition.CENTER, EyePosition.RIGHT]
            return np.random.choice(positions)
        return EyePosition.CENTER

    def _get_friendly_mode_name(self) -> str:
        """Convert robot state to friendly display name"""
        mode_names = {
            RobotState.MANUAL: "Manual Control",
            RobotState.FOLLOW: "Following",
            RobotState.REGISTRATION: "Registration",
            RobotState.QUESTION: "Q&A Mode",
            RobotState.MEDICINE: "Medicine Time",
            RobotState.HEALTH_CHECK: "Health Check",
            RobotState.IDLE: "Idle",
            RobotState.STARTING_UP: "Starting Up",
            RobotState.ERROR: "Error",
            RobotState.EMERGENCY: "Emergency"
        }
        return mode_names.get(self.current_robot_state, "Unknown")

    # Public interface methods

    def update_robot_state(self, state: str, ready: bool = False):
        """Update current robot state"""
        try:
            # Convert string to enum
            robot_state = RobotState(state.lower())

            with self.thread_lock:
                old_state = self.current_robot_state
                self.current_robot_state = robot_state
                self.robot_ready = ready

                if old_state != robot_state:
                    print(f"🤖 Display: Robot state changed {old_state.value} → {robot_state.value}")

                    # Handle special state transitions
                    if robot_state == RobotState.IDLE:
                        # Reset to normal eyes when entering idle
                        self.display_overlay.set_eye_emotion(EyeEmotion.NORMAL)
                        self.current_idle_emotion_index = 0
                        self.last_emotion_change = time.time()

        except ValueError:
            print(f"⚠️  Unknown robot state: {state}")

    def update_camera_feed(self, camera_frame: Optional[np.ndarray], is_active: bool = True):
        """Update camera feed"""
        with self.thread_lock:
            self.current_camera_frame = camera_frame.copy() if camera_frame is not None else None
            self.is_camera_active = is_active and camera_frame is not None

    def show_error(self, error_message: str, error_type: str = "warning"):
        """Show error message"""
        with self.thread_lock:
            self.current_error = error_message
            if error_type == "emergency":
                self.current_robot_state = RobotState.EMERGENCY
            else:
                self.current_robot_state = RobotState.ERROR

    def clear_error(self):
        """Clear current error and return to previous state"""
        with self.thread_lock:
            self.current_error = None
            if self.current_robot_state in [RobotState.ERROR, RobotState.EMERGENCY]:
                self.current_robot_state = RobotState.IDLE

    def set_eye_emotion(self, emotion: EyeEmotion):
        """Manually set eye emotion (overrides automatic cycling)"""
        with self.thread_lock:
            self.display_overlay.set_eye_emotion(emotion)

    def animate_eye_emotion(self, from_emotion: EyeEmotion, to_emotion: EyeEmotion, duration: float = 0.5):
        """Animate eye emotion transition"""
        self.display_overlay.animate_eye_transition(from_emotion, to_emotion, duration)

    def blink_eyes(self):
        """Trigger manual eye blink"""
        self.display_overlay.blink_eyes()

    def set_display_transparency(self, alpha: float):
        """Set display overlay transparency"""
        self.display_overlay.set_overlay_transparency(alpha)

    def get_status(self) -> Dict[str, Any]:
        """Get display overlay service status"""
        with self.thread_lock:
            return {
                'service_running': self.running,
                'robot_state': self.current_robot_state.value,
                'robot_ready': self.robot_ready,
                'camera_active': self.is_camera_active,
                'has_error': self.current_error is not None,
                'current_error': self.current_error,
                'overlay_status': self.display_overlay.get_status() if self.display_overlay else None
            }

    def shutdown(self):
        """Shutdown display overlay service"""
        try:
            self.running = False

            if self.service_thread and self.service_thread.is_alive():
                self.service_thread.join(timeout=2.0)

            if self.display_overlay:
                self.display_overlay.shutdown()

            print("✅ DisplayOverlayService: Shutdown completed")

        except Exception as e:
            print(f"⚠️  DisplayOverlayService shutdown error: {e}")


# Convenience functions for quick emotion changes

def express_happiness(service: DisplayOverlayService):
    """Express happiness through eyes"""
    service.animate_eye_emotion(EyeEmotion.NORMAL, EyeEmotion.LOVE, 0.5)

def express_concern(service: DisplayOverlayService):
    """Express concern through eyes"""
    service.animate_eye_emotion(EyeEmotion.NORMAL, EyeEmotion.SQUINTING, 0.3)

def express_sleepiness(service: DisplayOverlayService):
    """Express sleepiness through eyes"""
    service.animate_eye_emotion(EyeEmotion.NORMAL, EyeEmotion.SLEEPY, 0.8)

def express_surprise(service: DisplayOverlayService):
    """Express surprise through eyes (quick open-close)"""
    service.animate_eye_emotion(EyeEmotion.NORMAL, EyeEmotion.CLOSED, 0.1)
    # Will automatically return to normal due to blink behavior