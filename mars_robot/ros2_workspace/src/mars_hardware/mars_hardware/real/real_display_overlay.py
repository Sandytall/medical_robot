"""
Real Display Overlay Implementation for Mars Robot
Pygame-based display overlay with animated eyes, camera feeds, and status display
"""
import os
import sys
import time
import threading
import math
from typing import Dict, Any, Optional, Tuple, List
import numpy as np

try:
    import pygame
    import cv2
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from ..interfaces.display_overlay_interface import (
    DisplayOverlayInterface, EyeEmotion, EyePosition, DisplayMode
)


class RealDisplayOverlay(DisplayOverlayInterface):
    """Real display overlay implementation using pygame"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_initialized = False
        self.screen = None
        self.clock = None
        self.overlay_surface = None

        # Display settings
        display_config = self.config.get('display', {})
        self.screen_width = display_config.get('resolution', [800, 600])[0]
        self.screen_height = display_config.get('resolution', [800, 600])[1]
        self.background_color = tuple(display_config.get('background_color', [0, 0, 0]))

        # Eye settings
        self.eye_size = 120  # Size of each eye
        self.eye_spacing = 60  # Space between eyes
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

        # Eye bitmap data (converted from your C arrays)
        self._initialize_eye_bitmaps()

    def _initialize_eye_bitmaps(self):
        """Convert and initialize eye bitmap data"""
        # Convert your C bitmap arrays to numpy arrays
        self.eye_bitmaps = {}

        # Eye closed (horizontal line)
        eye_closed = np.zeros((32, 32), dtype=np.uint8)
        eye_closed[15:17, :] = 255
        self.eye_bitmaps['closed'] = eye_closed

        # Normal open eyes (oval)
        eye_normal = np.zeros((32, 32), dtype=np.uint8)
        for y in range(32):
            for x in range(32):
                # Create oval shape
                cx, cy = 16, 16
                if ((x - cx) / 12) ** 2 + ((y - cy) / 8) ** 2 <= 1:
                    eye_normal[y, x] = 255
        self.eye_bitmaps['normal'] = eye_normal

        # Sleepy eyes (half closed)
        eye_sleepy = np.zeros((32, 32), dtype=np.uint8)
        for y in range(32):
            for x in range(32):
                cx, cy = 16, 20  # Shifted down
                if ((x - cx) / 12) ** 2 + ((y - cy) / 6) ** 2 <= 1 and y >= 16:
                    eye_sleepy[y, x] = 255
        self.eye_bitmaps['sleepy'] = eye_sleepy

        # Looking left (pupil shifted)
        eye_look_left = np.zeros((32, 32), dtype=np.uint8)
        for y in range(32):
            for x in range(32):
                # Outer eye
                cx, cy = 16, 16
                if ((x - cx) / 12) ** 2 + ((y - cy) / 8) ** 2 <= 1:
                    eye_look_left[y, x] = 255
                # Pupil (shifted left)
                pcx, pcy = 12, 16
                if ((x - pcx) / 4) ** 2 + ((y - pcy) / 4) ** 2 <= 1:
                    eye_look_left[y, x] = 0  # Black pupil
        self.eye_bitmaps['look_left'] = eye_look_left

        # Looking right (pupil shifted)
        eye_look_right = np.zeros((32, 32), dtype=np.uint8)
        for y in range(32):
            for x in range(32):
                # Outer eye
                cx, cy = 16, 16
                if ((x - cx) / 12) ** 2 + ((y - cy) / 8) ** 2 <= 1:
                    eye_look_right[y, x] = 255
                # Pupil (shifted right)
                pcx, pcy = 20, 16
                if ((x - pcx) / 4) ** 2 + ((y - pcy) / 4) ** 2 <= 1:
                    eye_look_right[y, x] = 0  # Black pupil
        self.eye_bitmaps['look_right'] = eye_look_right

        # Squinting eyes (narrow)
        eye_squint = np.zeros((32, 32), dtype=np.uint8)
        for y in range(32):
            for x in range(32):
                cx, cy = 16, 16
                if ((x - cx) / 10) ** 2 + ((y - cy) / 4) ** 2 <= 1:
                    eye_squint[y, x] = 255
        self.eye_bitmaps['squint'] = eye_squint

        # Love eyes (heart shape)
        eye_love = np.zeros((32, 32), dtype=np.uint8)
        for y in range(32):
            for x in range(32):
                # Create heart shape (simplified)
                cx, cy = 16, 18
                if self._is_heart_shape(x - cx, y - cy):
                    eye_love[y, x] = 255
        self.eye_bitmaps['love'] = eye_love

    def _is_heart_shape(self, x, y):
        """Check if point is inside heart shape"""
        # Simplified heart equation
        x_norm = x / 8.0
        y_norm = y / 8.0
        return (x_norm**2 + y_norm**2 - 1)**3 - x_norm**2 * y_norm**3 <= 0

    def initialize(self) -> bool:
        """Initialize pygame display overlay"""
        if not PYGAME_AVAILABLE:
            print("❌ RealDisplayOverlay: pygame not available")
            return False

        try:
            # Initialize pygame
            pygame.init()

            # Set display mode with transparency support
            os.environ['SDL_VIDEODRIVER'] = 'x11'

            # Create display surface
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height),
                pygame.DOUBLEBUF | pygame.HWSURFACE
            )
            pygame.display.set_caption("Mars Robot Display Overlay")

            # Create overlay surface with per-pixel alpha
            self.overlay_surface = pygame.Surface(
                (self.screen_width, self.screen_height),
                pygame.SRCALPHA
            )

            # Initialize clock for animations
            self.clock = pygame.time.Clock()

            # Start display thread
            self.running = True
            self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
            self.display_thread.start()

            self.is_initialized = True
            print("✅ RealDisplayOverlay: Initialized successfully")
            return True

        except Exception as e:
            print(f"❌ RealDisplayOverlay initialization failed: {e}")
            return False

    def _display_loop(self):
        """Main display loop running in separate thread"""
        while self.running:
            try:
                with self.thread_lock:
                    # Clear overlay
                    self.overlay_surface.fill((0, 0, 0, 0))  # Transparent

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

                    # Apply overlay to screen
                    self.screen.fill(self.background_color)
                    self.screen.blit(self.overlay_surface, (0, 0))

                # Handle pygame events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False

                pygame.display.flip()
                self.clock.tick(60)  # 60 FPS

            except Exception as e:
                print(f"❌ Display loop error: {e}")
                time.sleep(0.1)

    def _draw_idle_eyes(self):
        """Draw animated eyes in idle mode"""
        try:
            # Handle blinking
            current_time = time.time()
            if current_time - self.last_blink_time > self.blink_interval:
                self._perform_blink()
                self.last_blink_time = current_time

            # Update animation
            self._update_eye_animation()

            # Calculate eye positions
            center_x = self.screen_width // 2
            center_y = self.screen_height // 2

            left_eye_x = center_x - self.eye_size - self.eye_spacing // 2
            right_eye_x = center_x + self.eye_spacing // 2
            eye_y = center_y - self.eye_size // 2

            # Draw eyes
            self._draw_single_eye(left_eye_x, eye_y, "left")
            self._draw_single_eye(right_eye_x, eye_y, "right")

            # Draw status indicators (small)
            self._draw_small_indicators()

        except Exception as e:
            print(f"❌ Eye drawing error: {e}")

    def _draw_single_eye(self, x: int, y: int, side: str):
        """Draw a single eye with current emotion and animation"""
        try:
            # Get appropriate bitmap based on emotion and position
            bitmap_name = self._get_bitmap_name()

            if bitmap_name not in self.eye_bitmaps:
                bitmap_name = 'normal'

            eye_bitmap = self.eye_bitmaps[bitmap_name]

            # Apply animation interpolation if animating
            if self.is_animating:
                target_bitmap_name = self._get_target_bitmap_name()
                if target_bitmap_name in self.eye_bitmaps:
                    target_bitmap = self.eye_bitmaps[target_bitmap_name]
                    # Interpolate between current and target
                    progress = self.animation_frame / self.animation_speed
                    progress = min(1.0, max(0.0, progress))
                    eye_bitmap = self._interpolate_bitmaps(eye_bitmap, target_bitmap, progress)

            # Convert numpy array to pygame surface
            eye_surface = self._numpy_to_pygame_surface(eye_bitmap)

            # Scale up the eye
            scaled_eye = pygame.transform.scale(eye_surface, (self.eye_size, self.eye_size))

            # Apply transparency
            scaled_eye.set_alpha(int(255 * self.overlay_alpha))

            # Draw to overlay
            self.overlay_surface.blit(scaled_eye, (x, y))

        except Exception as e:
            print(f"❌ Single eye drawing error: {e}")

    def _get_bitmap_name(self) -> str:
        """Get bitmap name based on current emotion and position"""
        if self.current_emotion == EyeEmotion.CLOSED:
            return 'closed'
        elif self.current_emotion == EyeEmotion.SLEEPY:
            return 'sleepy'
        elif self.current_emotion == EyeEmotion.SQUINTING:
            return 'squint'
        elif self.current_emotion == EyeEmotion.LOVE:
            return 'love'
        elif self.current_position == EyePosition.LEFT:
            return 'look_left'
        elif self.current_position == EyePosition.RIGHT:
            return 'look_right'
        else:
            return 'normal'

    def _get_target_bitmap_name(self) -> str:
        """Get target bitmap name for animation"""
        if self.target_emotion == EyeEmotion.CLOSED:
            return 'closed'
        elif self.target_emotion == EyeEmotion.SLEEPY:
            return 'sleepy'
        elif self.target_emotion == EyeEmotion.SQUINTING:
            return 'squint'
        elif self.target_emotion == EyeEmotion.LOVE:
            return 'love'
        elif self.target_position == EyePosition.LEFT:
            return 'look_left'
        elif self.target_position == EyePosition.RIGHT:
            return 'look_right'
        else:
            return 'normal'

    def _interpolate_bitmaps(self, bitmap1: np.ndarray, bitmap2: np.ndarray, progress: float) -> np.ndarray:
        """Smoothly interpolate between two bitmaps"""
        try:
            # Linear interpolation
            result = bitmap1 * (1.0 - progress) + bitmap2 * progress
            return result.astype(np.uint8)
        except:
            return bitmap1

    def _numpy_to_pygame_surface(self, array: np.ndarray) -> pygame.Surface:
        """Convert numpy array to pygame surface"""
        try:
            # Convert grayscale to RGB
            rgb_array = np.stack([array, array, array], axis=-1)

            # Create pygame surface
            surface = pygame.surfarray.make_surface(rgb_array.swapaxes(0, 1))
            return surface

        except Exception as e:
            print(f"❌ Numpy to pygame conversion error: {e}")
            # Return blank surface as fallback
            return pygame.Surface((32, 32))

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
            self.animate_eye_transition(original_emotion, EyeEmotion.CLOSED, 0.1)

            # Schedule eye opening
            def open_eyes():
                time.sleep(0.15)
                if self.running:
                    self.animate_eye_transition(EyeEmotion.CLOSED, original_emotion, 0.1)

            threading.Thread(target=open_eyes, daemon=True).start()

    def _draw_small_indicators(self):
        """Draw small status indicators"""
        try:
            # Small ready indicator in corner
            indicator_size = 20
            margin = 10

            # Ready indicator (green circle)
            if hasattr(self, 'robot_ready') and self.robot_ready:
                pygame.draw.circle(
                    self.overlay_surface,
                    (0, 255, 0, int(255 * self.overlay_alpha)),  # Green
                    (self.screen_width - margin - indicator_size // 2, margin + indicator_size // 2),
                    indicator_size // 2
                )

            # Mode indicator (small text)
            if hasattr(self, 'current_robot_mode'):
                font = pygame.font.Font(None, 24)
                text = font.render(self.current_robot_mode, True, (255, 255, 255))
                text.set_alpha(int(255 * self.overlay_alpha * 0.7))
                self.overlay_surface.blit(text, (margin, self.screen_height - margin - 24))

        except Exception as e:
            print(f"❌ Indicator drawing error: {e}")

    def _draw_camera_feed(self):
        """Draw camera feed overlay"""
        try:
            if hasattr(self, 'current_camera_frame') and self.current_camera_frame is not None:
                # Convert camera frame to pygame surface
                frame = self.current_camera_frame

                # Resize frame to fit screen
                frame_height, frame_width = frame.shape[:2]
                scale_x = self.screen_width / frame_width
                scale_y = self.screen_height / frame_height
                scale = min(scale_x, scale_y) * 0.8  # 80% of screen

                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)

                resized_frame = cv2.resize(frame, (new_width, new_height))

                # Convert BGR to RGB
                if len(resized_frame.shape) == 3:
                    resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

                # Convert to pygame surface
                frame_surface = pygame.surfarray.make_surface(resized_frame.swapaxes(0, 1))
                frame_surface.set_alpha(int(255 * self.overlay_alpha))

                # Center the frame
                x = (self.screen_width - new_width) // 2
                y = (self.screen_height - new_height) // 2

                self.overlay_surface.blit(frame_surface, (x, y))

                # Add camera frame border
                pygame.draw.rect(
                    self.overlay_surface,
                    (255, 255, 255, int(255 * self.overlay_alpha * 0.5)),
                    (x - 2, y - 2, new_width + 4, new_height + 4),
                    2
                )

        except Exception as e:
            print(f"❌ Camera feed drawing error: {e}")

    def _draw_status(self):
        """Draw status display"""
        try:
            if hasattr(self, 'status_text'):
                font = pygame.font.Font(None, 48)
                lines = self.status_text.split('\n')

                y_offset = 100
                for line in lines:
                    text_surface = font.render(line, True, (255, 255, 255))
                    text_surface.set_alpha(int(255 * self.overlay_alpha))

                    # Center text
                    text_rect = text_surface.get_rect()
                    x = (self.screen_width - text_rect.width) // 2

                    self.overlay_surface.blit(text_surface, (x, y_offset))
                    y_offset += text_rect.height + 10

        except Exception as e:
            print(f"❌ Status drawing error: {e}")

    def _draw_error(self):
        """Draw error display"""
        try:
            if hasattr(self, 'error_text'):
                # Error background
                error_rect = pygame.Rect(50, 50, self.screen_width - 100, 100)
                pygame.draw.rect(
                    self.overlay_surface,
                    (255, 0, 0, int(128 * self.overlay_alpha)),  # Semi-transparent red
                    error_rect
                )
                pygame.draw.rect(
                    self.overlay_surface,
                    (255, 255, 255, int(255 * self.overlay_alpha)),
                    error_rect,
                    3
                )

                # Error text
                font = pygame.font.Font(None, 36)
                text_surface = font.render(self.error_text, True, (255, 255, 255))
                text_surface.set_alpha(int(255 * self.overlay_alpha))

                text_rect = text_surface.get_rect()
                text_x = error_rect.centerx - text_rect.width // 2
                text_y = error_rect.centery - text_rect.height // 2

                self.overlay_surface.blit(text_surface, (text_x, text_y))

        except Exception as e:
            print(f"❌ Error drawing error: {e}")

    def _draw_mode_display(self):
        """Draw mode display"""
        try:
            if hasattr(self, 'mode_text'):
                # Mode background
                mode_rect = pygame.Rect(100, 200, self.screen_width - 200, 200)
                pygame.draw.rect(
                    self.overlay_surface,
                    (0, 100, 200, int(128 * self.overlay_alpha)),  # Semi-transparent blue
                    mode_rect
                )
                pygame.draw.rect(
                    self.overlay_surface,
                    (255, 255, 255, int(255 * self.overlay_alpha)),
                    mode_rect,
                    3
                )

                # Mode text
                font = pygame.font.Font(None, 64)
                text_surface = font.render(self.mode_text, True, (255, 255, 255))
                text_surface.set_alpha(int(255 * self.overlay_alpha))

                text_rect = text_surface.get_rect()
                text_x = mode_rect.centerx - text_rect.width // 2
                text_y = mode_rect.centery - text_rect.height // 2

                self.overlay_surface.blit(text_surface, (text_x, text_y))

                # Ready button if applicable
                if hasattr(self, 'show_ready_button') and self.show_ready_button:
                    ready_rect = pygame.Rect(mode_rect.centerx - 100, mode_rect.bottom + 20, 200, 50)
                    color = (0, 255, 0) if self.robot_ready else (150, 150, 150)
                    pygame.draw.rect(
                        self.overlay_surface,
                        (*color, int(128 * self.overlay_alpha)),
                        ready_rect
                    )

                    ready_font = pygame.font.Font(None, 36)
                    ready_text = "READY" if self.robot_ready else "NOT READY"
                    ready_surface = ready_font.render(ready_text, True, (255, 255, 255))
                    ready_surface.set_alpha(int(255 * self.overlay_alpha))

                    ready_text_rect = ready_surface.get_rect()
                    ready_x = ready_rect.centerx - ready_text_rect.width // 2
                    ready_y = ready_rect.centery - ready_text_rect.height // 2

                    self.overlay_surface.blit(ready_surface, (ready_x, ready_y))

        except Exception as e:
            print(f"❌ Mode drawing error: {e}")

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
            self.animation_speed = max(1, duration * 60)  # Convert to frames at 60 FPS
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
        """Set overlay transparency (0.0-1.0)"""
        with self.thread_lock:
            self.overlay_alpha = max(0.0, min(1.0, alpha))

    def get_status(self) -> Dict[str, Any]:
        """Get display overlay status"""
        return {
            'initialized': self.is_initialized,
            'pygame_available': PYGAME_AVAILABLE,
            'current_mode': self.current_display_mode.value,
            'current_emotion': self.current_emotion.value,
            'current_position': self.current_position.value,
            'is_animating': self.is_animating,
            'screen_resolution': [self.screen_width, self.screen_height],
            'overlay_alpha': self.overlay_alpha
        }

    def shutdown(self):
        """Shutdown the display overlay system"""
        try:
            self.running = False

            if self.display_thread and self.display_thread.is_alive():
                self.display_thread.join(timeout=2.0)

            if PYGAME_AVAILABLE:
                pygame.quit()

            self.is_initialized = False
            print("✅ RealDisplayOverlay: Shutdown completed")

        except Exception as e:
            print(f"⚠️  RealDisplayOverlay shutdown error: {e}")