"""
Mock Motor Implementation for Development
"""
from typing import Tuple, Dict, Any
import time
import numpy as np

from ..interfaces.motor_interface import MotorInterface


class MockMotors(MotorInterface):
    """Mock motor implementation for L298N dual motor driver"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Motor state
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.max_speed = 100.0
        self.is_initialized = False

        # Position simulation (for odometry)
        self.x_position = 0.0
        self.y_position = 0.0
        self.orientation = 0.0  # radians
        self.last_update_time = time.time()

    def initialize(self) -> bool:
        """Initialize mock motor driver"""
        self.is_initialized = True
        print("Mock motor driver initialized")
        print(f"Left motor pins: {self.config.get('left_motor', {})}")
        print(f"Right motor pins: {self.config.get('right_motor', {})}")
        return True

    def set_motor_speed(self, left_speed: float, right_speed: float):
        """Set motor speeds"""
        # Clamp speeds to valid range
        self.left_speed = max(-100.0, min(100.0, left_speed))
        self.right_speed = max(-100.0, min(100.0, right_speed))

        # Apply speed limit
        if abs(self.left_speed) > self.max_speed:
            self.left_speed = self.max_speed if self.left_speed > 0 else -self.max_speed
        if abs(self.right_speed) > self.max_speed:
            self.right_speed = self.max_speed if self.right_speed > 0 else -self.max_speed

        self._update_position()
        print(f"Mock motors set: Left={self.left_speed:.1f}%, Right={self.right_speed:.1f}%")

    def move_forward(self, speed: float = 50.0):
        """Move robot forward"""
        self.set_motor_speed(speed, speed)

    def move_backward(self, speed: float = 50.0):
        """Move robot backward"""
        self.set_motor_speed(-speed, -speed)

    def turn_left(self, speed: float = 50.0):
        """Turn robot left"""
        self.set_motor_speed(-speed, speed)

    def turn_right(self, speed: float = 50.0):
        """Turn robot right"""
        self.set_motor_speed(speed, -speed)

    def stop(self):
        """Stop both motors"""
        self.set_motor_speed(0.0, 0.0)
        print("Mock motors stopped")

    def emergency_stop(self):
        """Emergency stop with brake"""
        self.stop()
        print("Mock motors EMERGENCY STOP activated")

    def get_motor_speeds(self) -> Tuple[float, float]:
        """Get current motor speeds"""
        return (self.left_speed, self.right_speed)

    def set_speed_limit(self, max_speed: float):
        """Set maximum speed limit"""
        self.max_speed = max(0.0, min(100.0, max_speed))
        print(f"Mock motor speed limit set to {self.max_speed}%")

    def get_speed_limit(self) -> float:
        """Get current speed limit"""
        return self.max_speed

    def is_connected(self) -> bool:
        """Check if motor driver is connected"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get motor driver status and diagnostics"""
        return {
            'connected': self.is_connected(),
            'initialized': self.is_initialized,
            'left_speed': self.left_speed,
            'right_speed': self.right_speed,
            'speed_limit': self.max_speed,
            'position': {
                'x': self.x_position,
                'y': self.y_position,
                'orientation': self.orientation
            },
            'motor_config': {
                'left_motor': self.config.get('left_motor', {}),
                'right_motor': self.config.get('right_motor', {})
            }
        }

    def _update_position(self):
        """Update simulated robot position based on motor speeds"""
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Simple differential drive kinematics
        # Assume wheel separation of 0.3m and wheel radius of 0.05m
        wheel_separation = 0.3  # meters
        wheel_radius = 0.05  # meters

        # Convert speeds from percentage to m/s (arbitrary scaling)
        left_velocity = (self.left_speed / 100.0) * 1.0  # max 1 m/s
        right_velocity = (self.right_speed / 100.0) * 1.0

        # Calculate linear and angular velocities
        linear_velocity = (left_velocity + right_velocity) / 2.0
        angular_velocity = (right_velocity - left_velocity) / wheel_separation

        # Update position
        self.x_position += linear_velocity * dt * np.cos(self.orientation)
        self.y_position += linear_velocity * dt * np.sin(self.orientation)
        self.orientation += angular_velocity * dt

        # Normalize orientation
        while self.orientation > np.pi:
            self.orientation -= 2 * np.pi
        while self.orientation < -np.pi:
            self.orientation += 2 * np.pi

    def get_odometry(self) -> Dict[str, float]:
        """Get current odometry data"""
        self._update_position()
        return {
            'x': self.x_position,
            'y': self.y_position,
            'orientation': self.orientation,
            'linear_velocity': (self.left_speed + self.right_speed) / 2.0 / 100.0,
            'angular_velocity': (self.right_speed - self.left_speed) / 100.0
        }

    def reset_odometry(self):
        """Reset position to origin"""
        self.x_position = 0.0
        self.y_position = 0.0
        self.orientation = 0.0
        print("Mock motor odometry reset")

    def shutdown(self):
        """Shutdown motor driver"""
        self.stop()
        self.is_initialized = False
        print("Mock motor driver shutdown completed")