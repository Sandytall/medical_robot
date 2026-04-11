"""
Terminator Terminal Display Overlay Implementation for Mars Robot
Terminal-based display overlay with animated ASCII eyes, status display, and animations
"""
import os
import sys
import time
import threading
import math
import shutil
from typing import Dict, Any, Optional, Tuple, List
import numpy as np

from ..interfaces.display_overlay_interface import (
    DisplayOverlayInterface, EyeEmotion, EyePosition, DisplayMode
)


class TerminatorDisplayOverlay(DisplayOverlayInterface):
    """Terminal-based display overlay implementation for terminator"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_initialized = False

        # Terminal settings
        self.terminal_width, self.terminal_height = self._get_terminal_size()

        # Eye settings
        self.eye_width = 12  # Width of each ASCII eye
        self.eye_height = 6  # Height of each ASCII eye
        self.eye_spacing = 4  # Space between eyes
        self.current_emotion = EyeEmotion.NORMAL
        self.current_position = EyePosition.CENTER
        self.target_emotion = EyeEmotion.NORMAL
        self.target_position = EyePosition.CENTER

        # Animation settings
        self.animation_speed = 8.0  # Frames per emotion transition
        self.blink_timer = 0
        self.blink_interval = 3.0  # Seconds between blinks
        self.last_blink_time = time.time()

        # Display mode
        self.current_display_mode = DisplayMode.IDLE_EYES
        self.overlay_alpha = 0.9

        # Threading
        self.display_thread = None
        self.running = False
        self.thread_lock = threading.Lock()

        # Animation state
        self.animation_frame = 0
        self.is_animating = False

        # Display content
        self.status_text = ""
        self.error_text = ""
        self.mode_text = ""
        self.show_ready_button = False
        self.robot_ready = False
        self.current_robot_mode = "unknown"
        self.current_camera_frame = None

        # ASCII art for eyes
        self._initialize_eye_ascii()

        # ANSI escape codes
        self.CLEAR_SCREEN = '\033[2J'
        self.CLEAR_LINE = '\033[K'
        self.CURSOR_HOME = '\033[H'
        self.HIDE_CURSOR = '\033[?25l'
        self.SHOW_CURSOR = '\033[?25h'
        self.RESET_COLOR = '\033[0m'

        # Colors
        self.COLORS = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'bold': '\033[1m',
            'dim': '\033[2m'
        }

    def _get_terminal_size(self) -> Tuple[int, int]:
        """Get terminal dimensions"""
        try:
            size = shutil.get_terminal_size()
            return size.columns, size.lines
        except:
            return 80, 24  # Default fallback

    def _initialize_eye_ascii(self):
        """Initialize ASCII art representations for different eye states"""
        self.eye_ascii = {}

        # Normal eyes
        self.eye_ascii['normal'] = [
            "   ┌────┐   ",
            "  │ ●    │  ",
            " │       │ ",
            " │   ●   │ ",
            "  │      │  ",
            "   └────┘   "
        ]

        # Closed eyes (horizontal lines)
        self.eye_ascii['closed'] = [
            "   ┌────┐   ",
            "  │      │  ",
            " │   ──   │ ",
            " │   ──   │ ",
            "  │      │  ",
            "   └────┘   "
        ]

        # Sleepy eyes (half closed)
        self.eye_ascii['sleepy'] = [
            "   ┌────┐   ",
            "  │      │  ",
            " │       │ ",
            " │  ▄▄▄  │ ",
            "  │  ●  │  ",
            "   └────┘   "
        ]

        # Looking left
        self.eye_ascii['look_left'] = [
            "   ┌────┐   ",
            "  │●     │  ",
            " │       │ ",
            " │   ●   │ ",
            "  │      │  ",
            "   └────┘   "
        ]

        # Looking right
        self.eye_ascii['look_right'] = [
            "   ┌────┐   ",
            "  │     ●│  ",
            " │       │ ",
            " │   ●   │ ",
            "  │      │  ",
            "   └────┘   "
        ]

        # Squinting eyes
        self.eye_ascii['squint'] = [
            "   ┌────┐   ",
            "  │ ▄▄▄  │  ",
            " │  ▀ ▀  │ ",
            " │  ▄ ▄  │ ",
            "  │ ▀▀▀  │  ",
            "   └────┘   "
        ]

        # Love eyes (hearts)
        self.eye_ascii['love'] = [
            "   ┌────┐   ",
            "  │ ♡    │  ",
            " │   ♡   │ ",
            " │   ♡   │ ",
            "  │  ♡   │  ",
            "   └────┘   "
        ]

    def _cursor_to(self, x: int, y: int) -> str:
        """Move cursor to specific position"""
        return f'\033[{y};{x}H'

    def _print_at(self, x: int, y: int, text: str, color: str = ''):
        """Print text at specific terminal position"""
        try:
            sys.stdout.write(self._cursor_to(x, y))
            if color and color in self.COLORS:
                sys.stdout.write(self.COLORS[color])
            sys.stdout.write(text)
            sys.stdout.write(self.RESET_COLOR)
            sys.stdout.flush()
        except:
            pass

    def _clear_terminal(self):
        """Clear the terminal screen"""
        try:
            sys.stdout.write(self.CLEAR_SCREEN)
            sys.stdout.write(self.CURSOR_HOME)
            sys.stdout.write(self.HIDE_CURSOR)
            sys.stdout.flush()
        except:
            pass

    def _draw_border(self, title: str = "Mars Robot Display"):
        """Draw a border around the terminal display"""
        try:
            # Top border
            border_line = "╔" + "═" * (self.terminal_width - 2) + "╗"
            self._print_at(1, 1, border_line, 'cyan')

            # Title
            title_x = (self.terminal_width - len(title)) // 2
            self._print_at(title_x, 1, f"║{title}║", 'bold')

            # Side borders
            for y in range(2, self.terminal_height - 1):
                self._print_at(1, y, "║", 'cyan')
                self._print_at(self.terminal_width, y, "║", 'cyan')

            # Bottom border
            bottom_line = "╚" + "═" * (self.terminal_width - 2) + "╝"
            self._print_at(1, self.terminal_height - 1, bottom_line, 'cyan')

        except:
            pass

    def initialize(self) -> bool:
        """Initialize terminal display overlay"""
        try:
            # Check if running in a terminal
            if not sys.stdout.isatty():
                print("❌ TerminatorDisplayOverlay: Not running in a terminal")
                return False

            # Clear screen and setup
            self._clear_terminal()

            # Start display thread
            self.running = True
            self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
            self.display_thread.start()

            self.is_initialized = True
            print("✅ TerminatorDisplayOverlay: Initialized successfully")
            return True

        except Exception as e:
            print(f"❌ TerminatorDisplayOverlay initialization failed: {e}")
            return False

    def _display_loop(self):
        """Main display loop running in separate thread"""
        while self.running:
            try:
                with self.thread_lock:
                    # Update terminal size (in case window was resized)
                    self.terminal_width, self.terminal_height = self._get_terminal_size()

                    # Clear and redraw
                    self._clear_terminal()
                    self._draw_border()

                    # Handle different display modes
                    if self.current_display_mode == DisplayMode.IDLE_EYES:
                        self._draw_idle_eyes()
                    elif self.current_display_mode == DisplayMode.CAMERA_FEED:
                        self._draw_camera_feed()
                    elif self.current_display_mode == DisplayMode.STATUS_DISPLAY:
                        self._draw_status()
                    elif self.current_display_mode == DisplayMode.ERROR_DISPLAY:
                        self._draw_error()
                    elif self.current_display_mode == DisplayMode.MODE_DISPLAY:
                        self._draw_mode_display()

                    # Draw status line at bottom
                    self._draw_status_line()

                time.sleep(0.1)  # 10 FPS for terminal display

            except Exception as e:
                print(f"❌ Display loop error: {e}")
                time.sleep(0.5)

    def _draw_idle_eyes(self):
        """Draw animated ASCII eyes in idle mode"""
        try:
            # Handle blinking
            current_time = time.time()
            if current_time - self.last_blink_time > self.blink_interval:
                self._perform_blink()
                self.last_blink_time = current_time

            # Update animation
            self._update_eye_animation()

            # Get current eye art
            eye_art = self._get_current_eye_art()

            # Calculate center position for eyes
            center_x = self.terminal_width // 2
            center_y = self.terminal_height // 2

            # Draw left eye
            left_eye_x = center_x - self.eye_width - self.eye_spacing
            self._draw_eye_art(left_eye_x, center_y - self.eye_height // 2, eye_art)

            # Draw right eye
            right_eye_x = center_x + self.eye_spacing
            self._draw_eye_art(right_eye_x, center_y - self.eye_height // 2, eye_art)

            # Draw status indicators
            self._draw_small_indicators()

        except Exception as e:
            print(f"❌ Eye drawing error: {e}")

    def _draw_eye_art(self, x: int, y: int, eye_lines: List[str]):
        """Draw ASCII art for a single eye"""
        try:
            for i, line in enumerate(eye_lines):
                if y + i >= 2 and y + i < self.terminal_height - 1:  # Stay within border
                    self._print_at(max(2, x), y + i, line, 'white')
        except:
            pass

    def _get_current_eye_art(self) -> List[str]:
        """Get current eye ASCII art based on emotion and position"""
        if self.current_emotion == EyeEmotion.CLOSED:
            return self.eye_ascii['closed']
        elif self.current_emotion == EyeEmotion.SLEEPY:
            return self.eye_ascii['sleepy']
        elif self.current_emotion == EyeEmotion.SQUINTING:
            return self.eye_ascii['squint']
        elif self.current_emotion == EyeEmotion.LOVE:
            return self.eye_ascii['love']
        elif self.current_emotion == EyeEmotion.LOOKING_LEFT:
            return self.eye_ascii['look_left']
        elif self.current_emotion == EyeEmotion.LOOKING_RIGHT:
            return self.eye_ascii['look_right']
        elif self.current_position == EyePosition.LEFT:
            return self.eye_ascii['look_left']
        elif self.current_position == EyePosition.RIGHT:
            return self.eye_ascii['look_right']
        else:
            return self.eye_ascii['normal']

    def _update_eye_animation(self):
        """Update eye animation state"""
        if self.is_animating:
            self.animation_frame += 1
            if self.animation_frame >= self.animation_speed:
                # Animation complete
                self.current_emotion = self.target_emotion
                self.current_position = self.target_position
                self.is_animating = False
                self.animation_frame = 0

    def _perform_blink(self):
        """Perform automatic blinking animation"""
        if not self.is_animating:
            # Quick blink
            original_emotion = self.current_emotion
            self.animate_eye_transition(original_emotion, EyeEmotion.CLOSED, 0.2)

            # Schedule eye opening
            def open_eyes():
                time.sleep(0.3)
                if self.running:
                    self.animate_eye_transition(EyeEmotion.CLOSED, original_emotion, 0.2)

            threading.Thread(target=open_eyes, daemon=True).start()

    def _draw_small_indicators(self):
        """Draw small status indicators"""
        try:
            # Ready indicator in top right corner
            if hasattr(self, 'robot_ready') and self.robot_ready:
                self._print_at(self.terminal_width - 8, 3, "● READY", 'green')
            else:
                self._print_at(self.terminal_width - 12, 3, "○ NOT READY", 'red')

            # Mode indicator in top left
            if hasattr(self, 'current_robot_mode'):
                self._print_at(3, 3, f"Mode: {self.current_robot_mode}", 'yellow')

        except:
            pass

    def _draw_camera_feed(self):
        """Draw camera feed as ASCII art"""
        try:
            if hasattr(self, 'current_camera_frame') and self.current_camera_frame is not None:
                # For terminal, show placeholder for camera feed
                center_x = self.terminal_width // 2
                center_y = self.terminal_height // 2

                camera_box = [
                    "┌─────────────────────┐",
                    "│                     │",
                    "│     📹 CAMERA      │",
                    "│       FEED          │",
                    "│                     │",
                    "│   [Live Video]      │",
                    "│                     │",
                    "└─────────────────────┘"
                ]

                for i, line in enumerate(camera_box):
                    self._print_at(center_x - len(line) // 2, center_y - len(camera_box) // 2 + i, line, 'green')

        except:
            pass

    def _draw_status(self):
        """Draw status display"""
        try:
            if hasattr(self, 'status_text') and self.status_text:
                lines = self.status_text.split('\n')
                center_x = self.terminal_width // 2
                start_y = self.terminal_height // 2 - len(lines) // 2

                for i, line in enumerate(lines):
                    self._print_at(center_x - len(line) // 2, start_y + i, line, 'white')

        except:
            pass

    def _draw_error(self):
        """Draw error display"""
        try:
            if hasattr(self, 'error_text') and self.error_text:
                # Error box
                error_lines = [
                    "┌─────────────────────────────┐",
                    "│           ERROR!            │",
                    "├─────────────────────────────┤",
                    f"│ {self.error_text[:27]:27} │",
                    "└─────────────────────────────┘"
                ]

                center_x = self.terminal_width // 2
                center_y = self.terminal_height // 2

                for i, line in enumerate(error_lines):
                    self._print_at(center_x - len(line) // 2, center_y - len(error_lines) // 2 + i, line, 'red')

        except:
            pass

    def _draw_mode_display(self):
        """Draw mode display"""
        try:
            if hasattr(self, 'mode_text') and self.mode_text:
                # Mode box
                mode_lines = [
                    "┌─────────────────────────────┐",
                    "│        ROBOT MODE           │",
                    "├─────────────────────────────┤",
                    f"│ {self.mode_text[:27]:27} │",
                    "└─────────────────────────────┘"
                ]

                if hasattr(self, 'show_ready_button') and self.show_ready_button:
                    ready_status = "READY" if self.robot_ready else "NOT READY"
                    ready_color = "green" if self.robot_ready else "red"
                    mode_lines.append(f"     Status: {ready_status}")

                center_x = self.terminal_width // 2
                center_y = self.terminal_height // 2

                for i, line in enumerate(mode_lines):
                    color = 'green' if self.robot_ready and i == len(mode_lines) - 1 else 'blue'
                    self._print_at(center_x - len(line) // 2, center_y - len(mode_lines) // 2 + i, line, color)

        except:
            pass

    def _draw_status_line(self):
        """Draw status line at bottom of terminal"""
        try:
            status_y = self.terminal_height - 2
            status_line = f"Mars Robot | Mode: {self.current_robot_mode} | Ready: {self.robot_ready} | Time: {time.strftime('%H:%M:%S')}"
            # Truncate if too long
            if len(status_line) > self.terminal_width - 4:
                status_line = status_line[:self.terminal_width - 7] + "..."

            self._print_at(3, status_y, status_line, 'dim')

        except:
            pass

    # Interface implementation methods

    def update_display_mode(self, mode: DisplayMode):
        """Update the current display mode"""
        with self.thread_lock:
            self.current_display_mode = mode

    def show_camera_feed(self, camera_frame: np.ndarray):
        """Display camera feed overlay"""
        with self.thread_lock:
            self.current_camera_frame = camera_frame.copy()
            self.current_display_mode = DisplayMode.CAMERA_FEED

    def show_robot_mode(self, mode: str, ready: bool = False):
        """Display current robot mode and ready status"""
        with self.thread_lock:
            self.current_robot_mode = mode
            self.robot_ready = ready
            self.mode_text = f"Mode: {mode}"
            self.show_ready_button = True
            self.current_display_mode = DisplayMode.MODE_DISPLAY

    def show_error(self, error_message: str, error_type: str = "warning"):
        """Display error message overlay"""
        with self.thread_lock:
            self.error_text = f"{error_type.upper()}: {error_message}"
            self.current_display_mode = DisplayMode.ERROR_DISPLAY

    def show_idle_eyes(self, emotion: EyeEmotion = EyeEmotion.NORMAL,
                      position: EyePosition = EyePosition.CENTER):
        """Display animated eyes when in idle mode"""
        with self.thread_lock:
            self.current_display_mode = DisplayMode.IDLE_EYES
            self.set_eye_emotion(emotion)
            self.set_eye_position(position)

    def animate_eye_transition(self, from_emotion: EyeEmotion,
                              to_emotion: EyeEmotion, duration: float = 0.5):
        """Smooth animation between eye emotions"""
        with self.thread_lock:
            self.current_emotion = from_emotion
            self.target_emotion = to_emotion
            self.animation_speed = max(1, duration * 10)  # Convert to frames at 10 FPS
            self.animation_frame = 0
            self.is_animating = True

    def set_eye_emotion(self, emotion: EyeEmotion):
        """Set current eye emotion"""
        if not self.is_animating:
            with self.thread_lock:
                self.current_emotion = emotion

    def set_eye_position(self, position: EyePosition):
        """Set current eye position"""
        if not self.is_animating:
            with self.thread_lock:
                self.current_position = position

    def blink_eyes(self, duration: float = 0.15):
        """Perform blinking animation"""
        if not self.is_animating:
            current_emotion = self.current_emotion
            self.animate_eye_transition(current_emotion, EyeEmotion.CLOSED, duration / 2)

            # Schedule eye opening
            def open_eyes():
                time.sleep(duration)
                if self.running:
                    self.animate_eye_transition(EyeEmotion.CLOSED, current_emotion, duration / 2)

            threading.Thread(target=open_eyes, daemon=True).start()

    def clear_overlay(self):
        """Clear all overlay content"""
        with self.thread_lock:
            self.current_display_mode = DisplayMode.IDLE_EYES

    def set_overlay_transparency(self, alpha: float):
        """Set overlay transparency (0.0-1.0) - Not applicable for terminal"""
        with self.thread_lock:
            self.overlay_alpha = max(0.0, min(1.0, alpha))

    def get_status(self) -> Dict[str, Any]:
        """Get display overlay status"""
        return {
            'initialized': self.is_initialized,
            'terminal_available': sys.stdout.isatty(),
            'current_mode': self.current_display_mode.value,
            'current_emotion': self.current_emotion.value,
            'current_position': self.current_position.value,
            'is_animating': self.is_animating,
            'terminal_size': [self.terminal_width, self.terminal_height],
            'overlay_alpha': self.overlay_alpha
        }

    def shutdown(self):
        """Shutdown the display overlay system"""
        try:
            self.running = False

            if self.display_thread and self.display_thread.is_alive():
                self.display_thread.join(timeout=2.0)

            # Restore terminal
            sys.stdout.write(self.SHOW_CURSOR)
            sys.stdout.write(self.RESET_COLOR)
            sys.stdout.write(self.CLEAR_SCREEN)
            sys.stdout.write(self.CURSOR_HOME)
            sys.stdout.flush()

            self.is_initialized = False
            print("✅ TerminatorDisplayOverlay: Shutdown completed")

        except Exception as e:
            print(f"⚠️  TerminatorDisplayOverlay shutdown error: {e}")