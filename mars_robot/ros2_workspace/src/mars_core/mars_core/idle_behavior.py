#!/usr/bin/env python3
"""
Idle Behavior System for Mars Robot
Handles random movements, greetings, and ambient behaviors when robot is not actively engaged
"""
import time
import random
import threading
from typing import Dict, Any, List, Tuple
from enum import Enum

import rclpy
from rclpy.node import Node

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mars_hardware'))

from mars_hardware.interfaces.arm_interface import ArmSide
from mars_hardware.interfaces.display_interface import EmotionType


class IdleState(Enum):
    """Idle behavior states"""
    WAITING = "waiting"
    RANDOM_MOVEMENT = "random_movement"
    GREETING = "greeting"
    LOOKING_AROUND = "looking_around"
    AMBIENT_DISPLAY = "ambient_display"


class IdleBehavior(Node):
    """Idle behavior handler for ambient robot activities"""

    def __init__(self, hardware_manager, config: Dict[str, Any]):
        super().__init__('idle_behavior')

        self.hardware = hardware_manager
        self.config = config

        # Idle state
        self.idle_active = False
        self.current_state = IdleState.WAITING
        self.last_activity_time = time.time()

        # Configuration
        self.idle_config = self.config.get('modes', {}).get('idle', {})
        self.random_movements_enabled = self.idle_config.get('random_movements', {}).get('enabled', True)
        self.movement_interval = self.idle_config.get('random_movements', {}).get('movement_interval', [30, 60])

        # Available movements
        self.movements = self.idle_config.get('random_movements', {}).get('movements', [])

        # Greetings
        self.greetings = self.idle_config.get('greetings', [
            "Hello there!",
            "Good day!",
            "How are you feeling today?",
            "Welcome! I'm MARS, your hospital assistant."
        ])

        # Movement definitions
        self.movement_definitions = {
            'wave': {
                'description': 'Friendly wave gesture',
                'duration': 3.0,
                'positions': [
                    {'left': [0, 45, -45, 0], 'right': [0, 45, -45, 0]},
                    {'left': [0, 45, -45, -45], 'right': [0, 45, -45, 45]},
                    {'left': [0, 45, -45, 45], 'right': [0, 45, -45, -45]},
                    {'left': [0, 0, 0, 0], 'right': [0, 0, 0, 0]}
                ]
            },
            'look_around': {
                'description': 'Look around the environment',
                'duration': 5.0,
                'camera_positions': [
                    (-45, 0), (0, 0), (45, 0), (0, 15), (0, -15), (0, 0)
                ]
            },
            'greet': {
                'description': 'Greeting gesture',
                'duration': 2.0,
                'positions': [
                    {'left': [-30, 60, -30, 0], 'right': [30, 60, -30, 0]},
                    {'left': [0, 0, 0, 0], 'right': [0, 0, 0, 0]}
                ]
            },
            'stretch': {
                'description': 'Stretching motion',
                'duration': 4.0,
                'positions': [
                    {'left': [45, 90, -90, 0], 'right': [-45, 90, -90, 0]},
                    {'left': [0, 135, -45, 0], 'right': [0, 135, -45, 0]},
                    {'left': [0, 0, 0, 0], 'right': [0, 0, 0, 0]}
                ]
            },
            'attention_pose': {
                'description': 'Alert attention position',
                'duration': 2.0,
                'positions': [
                    {'left': [0, 30, 0, 0], 'right': [0, 30, 0, 0]},
                    {'left': [0, 0, 0, 0], 'right': [0, 0, 0, 0]}
                ]
            }
        }

        # Idle timing
        self.next_movement_time = time.time() + random.uniform(*self.movement_interval)

        self.get_logger().info("Idle Behavior system initialized")

    def start_idle_behavior(self) -> bool:
        """Start idle behavior"""
        try:
            if self.idle_active:
                return True

            self.idle_active = True
            self.current_state = IdleState.WAITING
            self.last_activity_time = time.time()

            # Set display to idle mode
            if self.hardware.display:
                self.hardware.display.show_idle_mode()

            # Start idle behavior thread
            threading.Thread(target=self._idle_behavior_loop, daemon=True).start()

            self.get_logger().info("Idle behavior started")
            return True

        except Exception as e:
            self.get_logger().error(f"Idle behavior start error: {e}")
            return False

    def stop_idle_behavior(self):
        """Stop idle behavior"""
        try:
            if not self.idle_active:
                return

            self.idle_active = False
            self.current_state = IdleState.WAITING

            # Return to home position
            if self.hardware.arms:
                self.hardware.arms.move_to_home_position()

            if self.hardware.camera_servos:
                self.hardware.camera_servos.center_camera()

            self.get_logger().info("Idle behavior stopped")

        except Exception as e:
            self.get_logger().error(f"Idle behavior stop error: {e}")

    def _idle_behavior_loop(self):
        """Main idle behavior loop"""
        try:
            while self.idle_active:
                try:
                    current_time = time.time()

                    # Check if it's time for a random movement
                    if (self.random_movements_enabled and
                        current_time >= self.next_movement_time and
                        self.current_state == IdleState.WAITING):

                        self._trigger_random_movement()

                    # Update current behavior state
                    self._update_current_behavior()

                    # Check for ambient display updates
                    self._update_ambient_display()

                    time.sleep(1.0)  # 1Hz update rate

                except Exception as e:
                    self.get_logger().error(f"Idle behavior loop error: {e}")
                    time.sleep(2.0)

        except Exception as e:
            self.get_logger().error(f"Idle behavior thread error: {e}")

    def _trigger_random_movement(self):
        """Trigger a random movement"""
        try:
            if not self.movements:
                return

            # Select random movement based on probability
            movement_choices = []
            for movement in self.movements:
                movement_name = movement['name']
                probability = movement.get('probability', 0.1)

                # Add multiple entries based on probability (higher probability = more entries)
                entries = max(1, int(probability * 10))
                movement_choices.extend([movement_name] * entries)

            if not movement_choices:
                return

            selected_movement = random.choice(movement_choices)

            self.get_logger().info(f"Executing idle movement: {selected_movement}")
            self._execute_movement(selected_movement)

            # Schedule next movement
            interval = random.uniform(*self.movement_interval)
            self.next_movement_time = time.time() + interval

        except Exception as e:
            self.get_logger().error(f"Random movement trigger error: {e}")

    def _execute_movement(self, movement_name: str):
        """Execute a specific movement"""
        try:
            if movement_name not in self.movement_definitions:
                self.get_logger().warning(f"Unknown movement: {movement_name}")
                return

            movement = self.movement_definitions[movement_name]
            self.current_state = IdleState.RANDOM_MOVEMENT

            self.get_logger().debug(f"Executing {movement['description']}")

            # Execute different types of movements
            if 'positions' in movement:
                self._execute_arm_movement(movement)
            elif 'camera_positions' in movement:
                self._execute_camera_movement(movement)

            # Return to waiting state
            self.current_state = IdleState.WAITING

        except Exception as e:
            self.get_logger().error(f"Movement execution error: {e}")

    def _execute_arm_movement(self, movement: Dict[str, Any]):
        """Execute arm movement sequence"""
        try:
            if not self.hardware.arms:
                return

            positions = movement['positions']
            duration = movement['duration']
            step_duration = duration / len(positions)

            for position in positions:
                if not self.idle_active:
                    break

                left_angles = position.get('left', [0, 0, 0, 0])
                right_angles = position.get('right', [0, 0, 0, 0])

                self.hardware.arms.set_arm_angles(ArmSide.LEFT, left_angles)
                self.hardware.arms.set_arm_angles(ArmSide.RIGHT, right_angles)

                time.sleep(step_duration)

        except Exception as e:
            self.get_logger().error(f"Arm movement execution error: {e}")

    def _execute_camera_movement(self, movement: Dict[str, Any]):
        """Execute camera movement sequence"""
        try:
            if not self.hardware.camera_servos:
                return

            positions = movement['camera_positions']
            duration = movement['duration']
            step_duration = duration / len(positions)

            for pan, tilt in positions:
                if not self.idle_active:
                    break

                self.hardware.camera_servos.set_pan_tilt(pan, tilt)
                time.sleep(step_duration)

        except Exception as e:
            self.get_logger().error(f"Camera movement execution error: {e}")

    def _update_current_behavior(self):
        """Update current behavior state"""
        try:
            # Check if robot should greet someone
            # This would integrate with face detection to greet new people

            pass  # Placeholder for now

        except Exception as e:
            self.get_logger().error(f"Behavior update error: {e}")

    def _update_ambient_display(self):
        """Update ambient display information"""
        try:
            if not self.hardware.display:
                return

            current_time = time.time()

            # Update display every 30 seconds with different information
            if int(current_time) % 30 == 0:
                self.current_state = IdleState.AMBIENT_DISPLAY

                display_options = [
                    ("Show time", self._show_current_time),
                    ("Show emotion", self._show_random_emotion),
                    ("Show status", self._show_system_status),
                    ("Show greeting", self._show_greeting_message)
                ]

                display_type, display_func = random.choice(display_options)
                display_func()

                time.sleep(1)  # Prevent rapid updates

        except Exception as e:
            self.get_logger().error(f"Ambient display update error: {e}")

    def _show_current_time(self):
        """Show current time on display"""
        try:
            current_time = time.strftime("%H:%M", time.localtime())
            date_str = time.strftime("%B %d", time.localtime())

            self.hardware.display.show_text(f"MARS Robot\n{current_time}\n{date_str}")

        except Exception as e:
            self.get_logger().error(f"Time display error: {e}")

    def _show_random_emotion(self):
        """Show random emotion"""
        try:
            positive_emotions = [EmotionType.HAPPY, EmotionType.EXCITED, EmotionType.NEUTRAL]
            emotion = random.choice(positive_emotions)

            self.hardware.display.show_emotion(emotion, 3.0)

        except Exception as e:
            self.get_logger().error(f"Emotion display error: {e}")

    def _show_system_status(self):
        """Show system status"""
        try:
            self.hardware.display.show_text("MARS Robot\nStatus: Ready\nSay 'Hey Mars'")

        except Exception as e:
            self.get_logger().error(f"Status display error: {e}")

    def _show_greeting_message(self):
        """Show greeting message"""
        try:
            greeting = random.choice(self.greetings)
            self.hardware.display.show_text(f"MARS Robot\n\n{greeting}")

        except Exception as e:
            self.get_logger().error(f"Greeting display error: {e}")

    def trigger_greeting(self) -> bool:
        """Trigger greeting behavior"""
        try:
            if not self.idle_active or self.current_state != IdleState.WAITING:
                return False

            self.current_state = IdleState.GREETING

            # Select random greeting
            greeting = random.choice(self.greetings)

            # Display happy emotion
            if self.hardware.display:
                self.hardware.display.show_emotion(EmotionType.HAPPY, 2.0)

            # Speak greeting
            if self.hardware.audio:
                self.hardware.audio.play_text(greeting)

            # Perform greeting gesture
            self._execute_movement('greet')

            self.current_state = IdleState.WAITING
            return True

        except Exception as e:
            self.get_logger().error(f"Greeting trigger error: {e}")
            return False

    def respond_to_presence(self) -> bool:
        """Respond to detected presence"""
        try:
            if not self.idle_active:
                return False

            # Simple acknowledgment of presence
            acknowledgments = [
                "Hello! I'm MARS. Say 'Hey Mars' if you need help.",
                "Good to see you! How can I assist you today?",
                "Hi there! I'm here if you need anything."
            ]

            acknowledgment = random.choice(acknowledgments)

            if self.hardware.audio:
                self.hardware.audio.play_text(acknowledgment)

            if self.hardware.display:
                self.hardware.display.show_emotion(EmotionType.HAPPY, 2.0)

            return True

        except Exception as e:
            self.get_logger().error(f"Presence response error: {e}")
            return False

    def add_custom_movement(self, name: str, movement_definition: Dict[str, Any]):
        """Add custom movement definition"""
        try:
            self.movement_definitions[name] = movement_definition
            self.get_logger().info(f"Added custom movement: {name}")

        except Exception as e:
            self.get_logger().error(f"Add custom movement error: {e}")

    def get_available_movements(self) -> List[str]:
        """Get list of available movements"""
        return list(self.movement_definitions.keys())

    def is_idle_active(self) -> bool:
        """Check if idle behavior is currently active"""
        return self.idle_active

    def get_idle_status(self) -> Dict[str, Any]:
        """Get current idle status"""
        return {
            'active': self.idle_active,
            'current_state': self.current_state.value,
            'next_movement_time': self.next_movement_time,
            'time_to_next_movement': max(0, self.next_movement_time - time.time()),
            'available_movements': list(self.movement_definitions.keys()),
            'random_movements_enabled': self.random_movements_enabled
        }

    def set_movement_frequency(self, min_interval: float, max_interval: float):
        """Set movement frequency interval"""
        try:
            self.movement_interval = [min_interval, max_interval]
            self.get_logger().info(f"Movement interval updated: {min_interval}-{max_interval}s")

        except Exception as e:
            self.get_logger().error(f"Movement frequency update error: {e}")

    def cleanup(self):
        """Cleanup idle behavior resources"""
        try:
            if self.idle_active:
                self.stop_idle_behavior()

        except Exception as e:
            self.get_logger().error(f"Idle behavior cleanup error: {e}")