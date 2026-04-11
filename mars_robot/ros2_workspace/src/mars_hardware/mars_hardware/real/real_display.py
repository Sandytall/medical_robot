"""Real Display Implementation for Raspberry Pi 5"""
import os
import time
import math
import threading
from typing import Dict, Any, Tuple, Optional
from ..interfaces.display_interface import DisplayInterface, EmotionType

try:
    import pygame
    import pygame.freetype
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class RealDisplay(DisplayInterface):
    """Real display implementation for Raspberry Pi 5 using pygame/framebuffer"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_initialized = False
        self.screen = None
        self.clock = None
        self.font = None
        self.large_font = None
        self.display_lock = threading.Lock()
        self.current_brightness = 0.8
        self.background_color = (20, 20, 40)  # Dark blue background

        # Display configuration
        display_config = self.config.get('display', {})
        self.device = display_config.get('device', '/dev/fb1')
        self.resolution = tuple(display_config.get('resolution', [800, 600]))
        self.fullscreen = display_config.get('fullscreen', True)

        # Colors
        self.colors = {
            'white': (255, 255, 255),
            'black': (0, 0, 0),
            'red': (255, 80, 80),
            'green': (80, 255, 80),
            'blue': (80, 80, 255),
            'yellow': (255, 255, 80),
            'orange': (255, 165, 80),
            'purple': (160, 80, 255),
            'cyan': (80, 255, 255),
            'gray': (128, 128, 128),
            'light_gray': (200, 200, 200),
            'dark_gray': (64, 64, 64)
        }

        # Emotion eye patterns
        self.emotion_patterns = {
            EmotionType.HAPPY: self._draw_happy_eyes,
            EmotionType.SAD: self._draw_sad_eyes,
            EmotionType.EXCITED: self._draw_excited_eyes,
            EmotionType.SLEEPING: self._draw_sleepy_eyes,
            EmotionType.CONFUSED: self._draw_confused_eyes,
            EmotionType.ANGRY: self._draw_angry_eyes,
            EmotionType.SURPRISED: self._draw_surprised_eyes,
            EmotionType.NEUTRAL: self._draw_normal_eyes
        }

        print(f"RealDisplay: Configured for {self.resolution[0]}x{self.resolution[1]} on {self.device}")

    def initialize(self) -> bool:
        """Initialize display using pygame"""
        if not PYGAME_AVAILABLE:
            print("❌ RealDisplay: pygame not available")
            return False

        try:
            # Set SDL video driver for framebuffer if specified
            if self.device.startswith('/dev/fb'):
                os.environ['SDL_VIDEODRIVER'] = 'fbcon'
                os.environ['SDL_FBDEV'] = self.device
            elif not os.environ.get('DISPLAY'):
                # Fallback for headless systems
                os.environ['SDL_VIDEODRIVER'] = 'dummy'

            # Initialize pygame
            pygame.init()
            pygame.freetype.init()

            # Set display mode
            flags = pygame.FULLSCREEN if self.fullscreen else 0
            self.screen = pygame.display.set_mode(self.resolution, flags)
            pygame.display.set_caption("Mars Robot Display")

            # Initialize clock and fonts
            self.clock = pygame.time.Clock()

            try:
                self.font = pygame.freetype.Font(None, 24)
                self.large_font = pygame.freetype.Font(None, 48)
            except:
                # Fallback to pygame font
                pygame.font.init()
                self.font = pygame.font.Font(None, 24)
                self.large_font = pygame.font.Font(None, 48)

            # Clear screen and show startup
            self.clear_display()
            self._draw_startup_screen()
            pygame.display.flip()

            self.is_initialized = True
            print(f"✅ RealDisplay: Initialized {self.resolution[0]}x{self.resolution[1]} display")
            return True

        except Exception as e:
            print(f"❌ RealDisplay initialization failed: {e}")
            return False

    def _draw_startup_screen(self):
        """Draw startup screen"""
        with self.display_lock:
            self.screen.fill(self.background_color)

            # Draw Mars Robot logo text
            title_text = "MARS ROBOT"
            subtitle_text = "Hospital Assistant System"

            # Center the text
            center_x = self.resolution[0] // 2
            center_y = self.resolution[1] // 2

            if hasattr(self.large_font, 'render'):
                # pygame.freetype
                title_rect = self.large_font.get_rect(title_text)
                self.large_font.render_to(self.screen, (center_x - title_rect.width // 2, center_y - 60),
                                        title_text, self.colors['cyan'])

                subtitle_rect = self.font.get_rect(subtitle_text)
                self.font.render_to(self.screen, (center_x - subtitle_rect.width // 2, center_y + 20),
                                  subtitle_text, self.colors['white'])
            else:
                # pygame.font fallback
                title_surface = self.large_font.render(title_text, True, self.colors['cyan'])
                title_rect = title_surface.get_rect(center=(center_x, center_y - 30))
                self.screen.blit(title_surface, title_rect)

                subtitle_surface = self.font.render(subtitle_text, True, self.colors['white'])
                subtitle_rect = subtitle_surface.get_rect(center=(center_x, center_y + 30))
                self.screen.blit(subtitle_surface, subtitle_rect)

    def show_emotion(self, emotion: EmotionType, duration: float = 0.0):
        """Show emotion on display"""
        if not self.is_initialized:
            return

        with self.display_lock:
            self.screen.fill(self.background_color)

            # Draw emotion pattern
            if emotion in self.emotion_patterns:
                self.emotion_patterns[emotion]()
            else:
                self._draw_normal_eyes()

            # Add emotion text
            emotion_text = emotion.value.title()
            self._draw_centered_text(emotion_text, y_offset=200, color=self.colors['white'])

            pygame.display.flip()

        # Hold for duration if specified
        if duration > 0:
            time.sleep(duration)

    def _draw_normal_eyes(self):
        """Draw normal circular eyes"""
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2 - 50
        eye_radius = 40
        pupil_radius = 15

        # Left eye
        pygame.draw.circle(self.screen, self.colors['white'], (center_x - 80, center_y), eye_radius)
        pygame.draw.circle(self.screen, self.colors['black'], (center_x - 80, center_y), pupil_radius)

        # Right eye
        pygame.draw.circle(self.screen, self.colors['white'], (center_x + 80, center_y), eye_radius)
        pygame.draw.circle(self.screen, self.colors['black'], (center_x + 80, center_y), pupil_radius)

    def _draw_happy_eyes(self):
        """Draw happy smiling eyes"""
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2 - 50

        # Happy arcs
        pygame.draw.arc(self.screen, self.colors['yellow'], (center_x - 120, center_y - 20, 80, 40), 0, math.pi, 8)
        pygame.draw.arc(self.screen, self.colors['yellow'], (center_x + 40, center_y - 20, 80, 40), 0, math.pi, 8)

    def _draw_sad_eyes(self):
        """Draw sad drooping eyes"""
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2 - 50

        # Sad arcs
        pygame.draw.arc(self.screen, self.colors['blue'], (center_x - 120, center_y - 20, 80, 40), math.pi, 2 * math.pi, 8)
        pygame.draw.arc(self.screen, self.colors['blue'], (center_x + 40, center_y - 20, 80, 40), math.pi, 2 * math.pi, 8)

    def _draw_excited_eyes(self):
        """Draw excited star-shaped eyes"""
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2 - 50

        # Star patterns
        for offset in [-80, 80]:
            x = center_x + offset
            points = []
            for i in range(10):
                angle = i * math.pi / 5
                radius = 30 if i % 2 == 0 else 15
                px = x + radius * math.cos(angle)
                py = center_y + radius * math.sin(angle)
                points.append((px, py))
            pygame.draw.polygon(self.screen, self.colors['orange'], points)

    def _draw_sleepy_eyes(self):
        """Draw sleepy half-closed eyes"""
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2 - 50

        # Half circles for sleepy eyes
        pygame.draw.arc(self.screen, self.colors['purple'], (center_x - 120, center_y - 20, 80, 40), 0, math.pi, 6)
        pygame.draw.arc(self.screen, self.colors['purple'], (center_x + 40, center_y - 20, 80, 40), 0, math.pi, 6)

    def _draw_confused_eyes(self):
        """Draw confused spiral eyes"""
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2 - 50

        # Spiral patterns
        for offset in [-80, 80]:
            x = center_x + offset
            for i in range(20):
                angle = i * math.pi / 3
                radius = i * 2
                px = x + radius * math.cos(angle)
                py = center_y + radius * math.sin(angle)
                pygame.draw.circle(self.screen, self.colors['yellow'], (int(px), int(py)), 2)

    def _draw_angry_eyes(self):
        """Draw angry angular eyes"""
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2 - 50

        # Angry triangles
        left_points = [(center_x - 120, center_y), (center_x - 80, center_y - 30), (center_x - 40, center_y)]
        right_points = [(center_x + 40, center_y), (center_x + 80, center_y - 30), (center_x + 120, center_y)]

        pygame.draw.polygon(self.screen, self.colors['red'], left_points)
        pygame.draw.polygon(self.screen, self.colors['red'], right_points)

    def _draw_surprised_eyes(self):
        """Draw surprised wide eyes"""
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2 - 50

        # Large circles for surprise
        pygame.draw.circle(self.screen, self.colors['white'], (center_x - 80, center_y), 50)
        pygame.draw.circle(self.screen, self.colors['black'], (center_x - 80, center_y), 25)

        pygame.draw.circle(self.screen, self.colors['white'], (center_x + 80, center_y), 50)
        pygame.draw.circle(self.screen, self.colors['black'], (center_x + 80, center_y), 25)

    def show_text(self, text: str, font_size: int = 24, color: Tuple[int, int, int] = (255, 255, 255)):
        """Show text on display"""
        if not self.is_initialized:
            return

        with self.display_lock:
            self.screen.fill(self.background_color)
            self._draw_centered_text(text, font_size=font_size, color=color)
            pygame.display.flip()

    def _draw_centered_text(self, text: str, y_offset: int = 0, font_size: int = 24, color: Tuple[int, int, int] = (255, 255, 255)):
        """Draw centered text"""
        center_x = self.resolution[0] // 2
        center_y = self.resolution[1] // 2 + y_offset

        font = self.large_font if font_size > 30 else self.font

        if hasattr(font, 'render'):
            # pygame.freetype
            text_rect = font.get_rect(text)
            font.render_to(self.screen, (center_x - text_rect.width // 2, center_y - text_rect.height // 2),
                          text, color)
        else:
            # pygame.font fallback
            text_surface = font.render(text, True, color)
            text_rect = text_surface.get_rect(center=(center_x, center_y))
            self.screen.blit(text_surface, text_rect)

    def show_status(self, status: str, level: str = "info"):
        """Show status message with appropriate color"""
        color_map = {
            'info': self.colors['cyan'],
            'warning': self.colors['yellow'],
            'error': self.colors['red'],
            'success': self.colors['green']
        }
        color = color_map.get(level, self.colors['white'])
        self.show_text(status, color=color)

    def show_progress(self, progress: float, message: str = ""):
        """Show progress bar with message"""
        if not self.is_initialized:
            return

        with self.display_lock:
            self.screen.fill(self.background_color)

            # Progress bar
            bar_width = 400
            bar_height = 30
            bar_x = (self.resolution[0] - bar_width) // 2
            bar_y = self.resolution[1] // 2

            # Background
            pygame.draw.rect(self.screen, self.colors['dark_gray'], (bar_x, bar_y, bar_width, bar_height))

            # Progress fill
            fill_width = int(bar_width * min(1.0, max(0.0, progress)))
            if fill_width > 0:
                pygame.draw.rect(self.screen, self.colors['green'], (bar_x, bar_y, fill_width, bar_height))

            # Border
            pygame.draw.rect(self.screen, self.colors['white'], (bar_x, bar_y, bar_width, bar_height), 2)

            # Progress text
            progress_text = f"{int(progress * 100)}%"
            self._draw_centered_text(progress_text, y_offset=-50)

            # Message
            if message:
                self._draw_centered_text(message, y_offset=100)

            pygame.display.flip()

    def show_patient_info(self, name: str, patient_id: str, status: str = ""):
        """Show patient information"""
        if not self.is_initialized:
            return

        with self.display_lock:
            self.screen.fill(self.background_color)

            # Patient icon (simple circle)
            pygame.draw.circle(self.screen, self.colors['cyan'],
                             (self.resolution[0] // 2, 150), 50)
            pygame.draw.circle(self.screen, self.colors['white'],
                             (self.resolution[0] // 2, 150), 50, 3)

            # Patient information
            self._draw_centered_text(f"Patient: {name}", y_offset=-80, font_size=32)
            self._draw_centered_text(f"ID: {patient_id}", y_offset=-20)

            if status:
                self._draw_centered_text(status, y_offset=80, color=self.colors['green'])

            pygame.display.flip()

    def show_medication_reminder(self, patient_name: str, medication: str, time: str):
        """Show medication reminder"""
        if not self.is_initialized:
            return

        with self.display_lock:
            self.screen.fill(self.colors['red'])  # Urgent background

            # Medicine icon
            pygame.draw.rect(self.screen, self.colors['white'],
                           (self.resolution[0] // 2 - 25, 100, 50, 60))
            pygame.draw.rect(self.screen, self.colors['red'],
                           (self.resolution[0] // 2 - 15, 110, 30, 10))

            # Reminder text
            self._draw_centered_text("MEDICATION REMINDER", y_offset=-100,
                                   font_size=40, color=self.colors['white'])
            self._draw_centered_text(f"{patient_name}", y_offset=-20, color=self.colors['white'])
            self._draw_centered_text(f"Take: {medication}", y_offset=40, color=self.colors['white'])
            self._draw_centered_text(f"Time: {time}", y_offset=100, color=self.colors['white'])

            pygame.display.flip()

    def show_question_mode(self):
        """Show question mode indicator"""
        self.show_emotion(EmotionType.NORMAL)
        self._draw_centered_text("Ask me anything!", y_offset=150, color=self.colors['cyan'])
        pygame.display.flip()

    def show_follow_mode(self, target_name: str = ""):
        """Show follow mode indicator"""
        self.show_emotion(EmotionType.EXCITED)
        text = f"Following {target_name}" if target_name else "Follow Mode"
        self._draw_centered_text(text, y_offset=150, color=self.colors['green'])
        pygame.display.flip()

    def show_manual_mode(self):
        """Show manual control mode"""
        self.show_emotion(EmotionType.NORMAL)
        self._draw_centered_text("Manual Control", y_offset=150, color=self.colors['orange'])
        pygame.display.flip()

    def show_idle_mode(self):
        """Show idle mode"""
        self.show_emotion(EmotionType.SLEEPY)

    def clear_display(self):
        """Clear the display"""
        if not self.is_initialized:
            return

        with self.display_lock:
            self.screen.fill(self.background_color)
            pygame.display.flip()

    def set_brightness(self, brightness: float):
        """Set display brightness (0.0 to 1.0)"""
        self.current_brightness = max(0.0, min(1.0, brightness))
        # Note: Actual brightness control would require hardware-specific commands

    def get_brightness(self) -> float:
        """Get current brightness"""
        return self.current_brightness

    def set_background_color(self, color: Tuple[int, int, int]):
        """Set background color"""
        self.background_color = color

    def animate_emotion(self, emotion: EmotionType, animation_type: str = "pulse"):
        """Animate emotion display"""
        if not self.is_initialized:
            return

        # Simple pulse animation
        for i in range(10):
            alpha = 0.5 + 0.5 * math.sin(i * math.pi / 5)
            adjusted_emotion = emotion  # Could modify based on alpha
            self.show_emotion(adjusted_emotion)
            time.sleep(0.1)

    def show_custom_image(self, image_path: str):
        """Show custom image if it exists"""
        if not self.is_initialized or not os.path.exists(image_path):
            return

        try:
            with self.display_lock:
                image = pygame.image.load(image_path)
                image = pygame.transform.scale(image, self.resolution)
                self.screen.blit(image, (0, 0))
                pygame.display.flip()
        except Exception as e:
            print(f"❌ RealDisplay image load error: {e}")

    def get_display_resolution(self) -> Tuple[int, int]:
        """Get display resolution"""
        return self.resolution

    def is_connected(self) -> bool:
        """Check if display is connected"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get display status"""
        return {
            'initialized': self.is_initialized,
            'resolution': self.resolution,
            'brightness': self.current_brightness,
            'device': self.device,
            'pygame_available': PYGAME_AVAILABLE,
            'fullscreen': self.fullscreen
        }

    def shutdown(self):
        """Shutdown display and cleanup resources"""
        try:
            if self.is_initialized:
                with self.display_lock:
                    self.clear_display()
                    if self.screen:
                        pygame.display.quit()
                    pygame.quit()

                self.is_initialized = False
                print("✅ RealDisplay: Shutdown completed")

        except Exception as e:
            print(f"⚠️  RealDisplay shutdown error: {e}")