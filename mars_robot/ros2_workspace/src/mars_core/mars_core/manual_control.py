#!/usr/bin/env python3
"""
Manual Control System for Mars Robot
Handles "Hey Mars manual mode" functionality with gamepad control
"""
import time
import json
import threading
from typing import Dict, Any, Optional, Tuple
from enum import Enum

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

from std_msgs.msg import String, Bool, Float32
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Pygame not available for gamepad support")


class SpeedLevel(Enum):
    """Speed level enumeration"""
    SLOW = 0
    NORMAL = 1
    FAST = 2


class ManualControl(Node):
    """Manual control handler for gamepad input"""

    def __init__(self, hardware_manager, config: Dict[str, Any]):
        super().__init__('manual_control')

        self.hardware = hardware_manager
        self.config = config

        # Manual control state
        self.manual_active = False
        self.gamepad_connected = False
        self.last_input_time = time.time()

        # Speed control
        self.speed_levels = {
            SpeedLevel.SLOW: 0.3,
            SpeedLevel.NORMAL: 0.6,
            SpeedLevel.FAST: 1.0
        }
        self.current_speed_level = SpeedLevel.NORMAL

        # Movement state
        self.current_linear = 0.0
        self.current_angular = 0.0
        self.deadzone = 0.1

        # Gamepad state
        self.button_states = {}
        self.axis_values = {}
        self.last_emergency_button_time = 0

        # QoS profiles
        self.reliable_qos = QoSProfile(reliability=QoSReliabilityPolicy.RELIABLE, depth=10)

        # Publishers
        self.movement_pub = self.create_publisher(Twist, '/manual/cmd_vel', self.reliable_qos)
        self.status_pub = self.create_publisher(String, '/manual/status', self.reliable_qos)

        # Subscribers
        self.joy_sub = self.create_subscription(Joy, '/joy', self.joy_callback, self.reliable_qos)

        # Timers
        self.control_timer = self.create_timer(0.05, self.control_update_loop)  # 20Hz control loop
        self.status_timer = self.create_timer(1.0, self.publish_status)  # 1Hz status

        # Initialize gamepad if available
        self.gamepad = None
        self._initialize_gamepad()

        self.get_logger().info("Manual Control system initialized")

    def _initialize_gamepad(self):
        """Initialize gamepad interface"""
        try:
            if PYGAME_AVAILABLE:
                pygame.init()
                pygame.joystick.init()

                joystick_count = pygame.joystick.get_count()
                if joystick_count > 0:
                    self.gamepad = pygame.joystick.Joystick(0)
                    self.gamepad.init()
                    self.gamepad_connected = True
                    self.get_logger().info(f"Gamepad connected: {self.gamepad.get_name()}")
                else:
                    self.get_logger().warning("No gamepad detected")
            else:
                self.get_logger().warning("Pygame not available - gamepad support disabled")

        except Exception as e:
            self.get_logger().error(f"Gamepad initialization error: {e}")
            self.gamepad_connected = False

    def start_manual_control(self) -> bool:
        """Start manual control mode"""
        try:
            if self.manual_active:
                self.get_logger().warning("Manual control already active")
                return False

            # Check if gamepad is connected
            if not self.gamepad_connected:
                if self.hardware.audio:
                    self.hardware.audio.play_text("No gamepad detected. Please connect a gamepad and try again.")
                return False

            self.manual_active = True
            self.last_input_time = time.time()

            # Set display to manual mode
            if self.hardware.display:
                self.hardware.display.show_manual_mode()

            # Announce manual mode activation
            if self.hardware.audio:
                self.hardware.audio.play_text("Manual control mode activated. Use the gamepad to control my movement.")

            # Start gamepad monitoring
            if self.gamepad_connected:
                threading.Thread(target=self._gamepad_monitor_thread, daemon=True).start()

            self.get_logger().info("Manual control mode started")
            return True

        except Exception as e:
            self.get_logger().error(f"Manual control start error: {e}")
            return False

    def stop_manual_control(self):
        """Stop manual control mode"""
        try:
            if not self.manual_active:
                return

            self.manual_active = False

            # Stop robot movement
            self._stop_robot_movement()

            # Announce mode exit
            if self.hardware.audio:
                self.hardware.audio.play_text("Manual control mode deactivated")

            self.get_logger().info("Manual control mode stopped")

        except Exception as e:
            self.get_logger().error(f"Manual control stop error: {e}")

    def _gamepad_monitor_thread(self):
        """Monitor gamepad input in separate thread"""
        try:
            clock = pygame.time.Clock() if PYGAME_AVAILABLE else None

            while self.manual_active and self.gamepad_connected:
                if PYGAME_AVAILABLE:
                    # Process pygame events
                    for event in pygame.event.get():
                        if event.type == pygame.JOYBUTTONDOWN:
                            self._handle_button_press(event.button, True)
                        elif event.type == pygame.JOYBUTTONUP:
                            self._handle_button_press(event.button, False)
                        elif event.type == pygame.JOYAXISMOTION:
                            self._handle_axis_motion(event.axis, event.value)

                    if clock:
                        clock.tick(60)  # 60 FPS
                else:
                    time.sleep(0.016)  # ~60 FPS equivalent

        except Exception as e:
            self.get_logger().error(f"Gamepad monitoring error: {e}")

    def joy_callback(self, msg: Joy):
        """Handle ROS joy messages (if using ros joy driver)"""
        try:
            if not self.manual_active:
                return

            self.last_input_time = time.time()

            # Process buttons
            for i, button_pressed in enumerate(msg.buttons):
                if i in self.button_states:
                    # Check for button state change
                    if button_pressed != self.button_states[i]:
                        self._handle_button_press(i, bool(button_pressed))

                self.button_states[i] = bool(button_pressed)

            # Process axes
            for i, axis_value in enumerate(msg.axes):
                self._handle_axis_motion(i, axis_value)

        except Exception as e:
            self.get_logger().error(f"Joy callback error: {e}")

    def _handle_button_press(self, button: int, pressed: bool):
        """Handle gamepad button press/release"""
        try:
            self.button_states[button] = pressed

            if pressed:
                self.get_logger().debug(f"Button {button} pressed")

                # Button mappings (standard Xbox/PlayStation layout)
                if button == 0:  # A/X button - Emergency stop
                    current_time = time.time()
                    if current_time - self.last_emergency_button_time > 1.0:  # Prevent spam
                        self.emergency_stop()
                        self.last_emergency_button_time = current_time

                elif button == 1:  # B/Circle button - Exit manual mode
                    self.stop_manual_control()

                elif button == 4:  # LB/L1 - Decrease speed level
                    self._change_speed_level(-1)

                elif button == 5:  # RB/R1 - Increase speed level
                    self._change_speed_level(1)

                elif button == 6:  # Back/Select - Reset to center
                    self._center_robot()

                elif button == 7:  # Start - Show status
                    self._announce_status()

        except Exception as e:
            self.get_logger().error(f"Button handling error: {e}")

    def _handle_axis_motion(self, axis: int, value: float):
        """Handle gamepad axis motion"""
        try:
            # Apply deadzone
            if abs(value) < self.deadzone:
                value = 0.0

            self.axis_values[axis] = value
            self.last_input_time = time.time()

            # Calculate robot movement based on axis input
            self._calculate_robot_movement()

        except Exception as e:
            self.get_logger().error(f"Axis handling error: {e}")

    def _calculate_robot_movement(self):
        """Calculate robot movement from gamepad input"""
        try:
            # Standard gamepad mapping
            # Left stick Y (axis 1) = forward/backward (inverted)
            # Right stick X (axis 3) = left/right turning

            left_stick_y = -self.axis_values.get(1, 0.0)  # Invert Y axis
            right_stick_x = self.axis_values.get(3, 0.0)

            # Get current speed multiplier
            speed_multiplier = self.speed_levels[self.current_speed_level]

            # Calculate linear and angular velocities
            linear_velocity = left_stick_y * speed_multiplier
            angular_velocity = right_stick_x * speed_multiplier

            # Update current velocities
            self.current_linear = linear_velocity
            self.current_angular = angular_velocity

            # Send movement commands to hardware
            self._send_movement_command(linear_velocity, angular_velocity)

        except Exception as e:
            self.get_logger().error(f"Movement calculation error: {e}")

    def _send_movement_command(self, linear: float, angular: float):
        """Send movement command to robot"""
        try:
            # Calculate differential drive motor speeds
            # Assume wheel separation of 0.3m for differential drive
            wheel_separation = 0.3
            max_wheel_speed = 1.0  # Maximum wheel speed

            # Convert to left/right motor speeds
            left_speed = (linear - angular * wheel_separation / 2) / max_wheel_speed * 100.0
            right_speed = (linear + angular * wheel_separation / 2) / max_wheel_speed * 100.0

            # Clamp speeds to valid range
            left_speed = max(-100.0, min(100.0, left_speed))
            right_speed = max(-100.0, min(100.0, right_speed))

            # Send to motors
            if self.hardware.motors:
                self.hardware.motors.set_motor_speed(left_speed, right_speed)

            # Also publish ROS twist message
            twist_msg = Twist()
            twist_msg.linear.x = linear
            twist_msg.angular.z = angular
            self.movement_pub.publish(twist_msg)

            # Log significant movements
            if abs(linear) > 0.1 or abs(angular) > 0.1:
                self.get_logger().debug(
                    f"Movement: Linear={linear:.2f}, Angular={angular:.2f}, "
                    f"Motors: L={left_speed:.1f}%, R={right_speed:.1f}%"
                )

        except Exception as e:
            self.get_logger().error(f"Movement command error: {e}")

    def _change_speed_level(self, direction: int):
        """Change speed level (direction: -1 for decrease, +1 for increase)"""
        try:
            speed_levels = list(SpeedLevel)
            current_index = speed_levels.index(self.current_speed_level)

            new_index = current_index + direction
            if 0 <= new_index < len(speed_levels):
                self.current_speed_level = speed_levels[new_index]
                speed_value = self.speed_levels[self.current_speed_level]

                self.get_logger().info(f"Speed level changed to {self.current_speed_level.name} ({speed_value:.1f})")

                # Announce speed change
                if self.hardware.audio:
                    self.hardware.audio.play_text(f"Speed set to {self.current_speed_level.name.lower()}")

                # Update display
                if self.hardware.display:
                    self.hardware.display.show_status(f"Speed: {self.current_speed_level.name}", "info")

        except Exception as e:
            self.get_logger().error(f"Speed level change error: {e}")

    def _center_robot(self):
        """Center robot and stop movement"""
        try:
            self._stop_robot_movement()

            if self.hardware.audio:
                self.hardware.audio.play_text("Robot centered")

            self.get_logger().info("Robot movement centered")

        except Exception as e:
            self.get_logger().error(f"Robot centering error: {e}")

    def _stop_robot_movement(self):
        """Stop all robot movement"""
        try:
            # Stop motors
            if self.hardware.motors:
                self.hardware.motors.stop()

            # Reset velocities
            self.current_linear = 0.0
            self.current_angular = 0.0

            # Publish zero twist
            twist_msg = Twist()
            self.movement_pub.publish(twist_msg)

        except Exception as e:
            self.get_logger().error(f"Stop movement error: {e}")

    def emergency_stop(self):
        """Execute emergency stop"""
        try:
            self.get_logger().warning("Manual control emergency stop activated")

            # Stop all movement
            self._stop_robot_movement()

            # Stop manual control mode
            self.manual_active = False

            # Notify system
            if self.hardware.audio:
                self.hardware.audio.play_sound_effect('alert')
                self.hardware.audio.play_text("Emergency stop activated")

            if self.hardware.display:
                self.hardware.display.show_status("EMERGENCY STOP", "error")

        except Exception as e:
            self.get_logger().error(f"Emergency stop error: {e}")

    def _announce_status(self):
        """Announce current manual control status"""
        try:
            status_text = f"Manual control active. Speed level: {self.current_speed_level.name.lower()}"

            if self.hardware.audio:
                self.hardware.audio.play_text(status_text)

            # Show detailed status on display
            if self.hardware.display:
                self.hardware.display.show_text(
                    f"Manual Control\n"
                    f"Speed: {self.current_speed_level.name}\n"
                    f"Linear: {self.current_linear:.2f}\n"
                    f"Angular: {self.current_angular:.2f}"
                )

        except Exception as e:
            self.get_logger().error(f"Status announcement error: {e}")

    def control_update_loop(self):
        """Control loop for manual mode"""
        try:
            if not self.manual_active:
                return

            # Check for input timeout
            input_timeout = 10.0  # Stop if no input for 10 seconds
            if time.time() - self.last_input_time > input_timeout:
                self.get_logger().info("Manual control input timeout - stopping movement")
                self._stop_robot_movement()
                self.last_input_time = time.time()  # Reset timer

            # Check gamepad connection
            if self.gamepad_connected and PYGAME_AVAILABLE:
                try:
                    # Check if gamepad is still connected
                    if pygame.joystick.get_count() == 0:
                        self.get_logger().warning("Gamepad disconnected")
                        self.gamepad_connected = False
                        self.stop_manual_control()
                except:
                    pass

        except Exception as e:
            self.get_logger().error(f"Control update error: {e}")

    def publish_status(self):
        """Publish manual control status"""
        try:
            status_data = {
                'active': self.manual_active,
                'gamepad_connected': self.gamepad_connected,
                'speed_level': self.current_speed_level.name,
                'current_linear': self.current_linear,
                'current_angular': self.current_angular,
                'button_states': self.button_states,
                'axis_values': self.axis_values,
                'last_input_time': self.last_input_time
            }

            status_msg = String()
            status_msg.data = json.dumps(status_data)
            self.status_pub.publish(status_msg)

        except Exception as e:
            self.get_logger().error(f"Status publishing error: {e}")

    def get_control_status(self) -> Dict[str, Any]:
        """Get current control status"""
        return {
            'active': self.manual_active,
            'gamepad_connected': self.gamepad_connected,
            'speed_level': self.current_speed_level.name,
            'speed_value': self.speed_levels[self.current_speed_level],
            'current_linear': self.current_linear,
            'current_angular': self.current_angular,
            'last_input_time': self.last_input_time
        }

    def is_manual_active(self) -> bool:
        """Check if manual control is currently active"""
        return self.manual_active

    def cleanup(self):
        """Cleanup manual control resources"""
        try:
            if self.manual_active:
                self.stop_manual_control()

            if self.gamepad and PYGAME_AVAILABLE:
                self.gamepad.quit()
                pygame.quit()

        except Exception as e:
            self.get_logger().error(f"Manual control cleanup error: {e}")