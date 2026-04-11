#!/usr/bin/env python3
"""
Mars Robot Terminator Display Starter
Run this script in terminator to start the display overlay
"""
import sys
import time
import signal
import os

# Add the ROS2 workspace to Python path
sys.path.insert(0, '/home/sandeep/pi5/mars_robot/ros2_workspace/src')

from mars_hardware.mars_hardware.real.terminator_display_overlay import TerminatorDisplayOverlay
from mars_hardware.mars_hardware.interfaces.display_overlay_interface import EyeEmotion, EyePosition


class TerminatorDisplayApp:
    """Simple standalone application for terminator display"""

    def __init__(self):
        self.display = None
        self.running = False

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n🔄 Shutting down display overlay...")
        self.running = False
        if self.display:
            self.display.shutdown()
        sys.exit(0)

    def run(self):
        """Main application loop"""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        print("🚀 Starting Mars Robot Terminator Display Overlay...")
        print("Press Ctrl+C to quit")
        print("=" * 50)

        # Initialize display
        config = {
            'display_overlay': {
                'resolution': [80, 24]  # Default terminal size
            }
        }

        self.display = TerminatorDisplayOverlay(config)

        if not self.display.initialize():
            print("❌ Failed to initialize terminator display overlay")
            return 1

        # Start with idle eyes
        self.display.show_idle_eyes()
        self.running = True

        # Demo sequence
        try:
            # Show different emotions
            emotions = [
                (EyeEmotion.NORMAL, "Normal eyes"),
                (EyeEmotion.SLEEPY, "Sleepy eyes"),
                (EyeEmotion.LOVE, "Love eyes"),
                (EyeEmotion.SQUINTING, "Squinting"),
                (EyeEmotion.LOOKING_LEFT, "Looking left"),
                (EyeEmotion.LOOKING_RIGHT, "Looking right")
            ]

            emotion_index = 0
            last_emotion_change = time.time()
            emotion_interval = 5.0  # Change emotion every 5 seconds

            # Keep running and cycling through emotions
            while self.running:
                current_time = time.time()

                # Change emotion periodically for demonstration
                if current_time - last_emotion_change > emotion_interval:
                    emotion, description = emotions[emotion_index]
                    self.display.set_eye_emotion(emotion)
                    emotion_index = (emotion_index + 1) % len(emotions)
                    last_emotion_change = current_time

                time.sleep(0.5)

        except KeyboardInterrupt:
            pass

        finally:
            self.display.shutdown()

        print("\n✅ Terminator display overlay stopped")
        return 0


if __name__ == "__main__":
    app = TerminatorDisplayApp()
    exit_code = app.run()
    sys.exit(exit_code)