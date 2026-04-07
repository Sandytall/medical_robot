"""
Motor Interface for L298N Dual Motor Driver
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any


class MotorInterface(ABC):
    """Abstract interface for dual motor control (left/right wheel drive)"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize motor driver hardware"""
        pass

    @abstractmethod
    def set_motor_speed(self, left_speed: float, right_speed: float):
        """
        Set motor speeds
        Args:
            left_speed: Speed for left motor (-100.0 to 100.0, negative = reverse)
            right_speed: Speed for right motor (-100.0 to 100.0, negative = reverse)
        """
        pass

    @abstractmethod
    def move_forward(self, speed: float = 50.0):
        """Move robot forward at given speed (0-100)"""
        pass

    @abstractmethod
    def move_backward(self, speed: float = 50.0):
        """Move robot backward at given speed (0-100)"""
        pass

    @abstractmethod
    def turn_left(self, speed: float = 50.0):
        """Turn robot left at given speed (0-100)"""
        pass

    @abstractmethod
    def turn_right(self, speed: float = 50.0):
        """Turn robot right at given speed (0-100)"""
        pass

    @abstractmethod
    def stop(self):
        """Stop both motors immediately"""
        pass

    @abstractmethod
    def emergency_stop(self):
        """Emergency stop with brake"""
        pass

    @abstractmethod
    def get_motor_speeds(self) -> Tuple[float, float]:
        """Get current motor speeds as (left_speed, right_speed)"""
        pass

    @abstractmethod
    def set_speed_limit(self, max_speed: float):
        """Set maximum speed limit (0-100)"""
        pass

    @abstractmethod
    def get_speed_limit(self) -> float:
        """Get current speed limit"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if motor driver is connected"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get motor driver status and diagnostics"""
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown motor driver and release resources"""
        pass