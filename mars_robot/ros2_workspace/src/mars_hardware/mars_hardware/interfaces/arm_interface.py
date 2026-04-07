"""
Arm Interface for Robotic Arm Management (2 arms × 4 servos each)
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from enum import Enum


class ArmSide(Enum):
    LEFT = "left"
    RIGHT = "right"


class ArmInterface(ABC):
    """Abstract interface for robotic arm control"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize all servo motors"""
        pass

    @abstractmethod
    def set_servo_angle(self, arm: ArmSide, joint: int, angle: float):
        """
        Set individual servo angle
        Args:
            arm: Left or right arm
            joint: Joint number (0-3)
            angle: Angle in degrees (servo-dependent range)
        """
        pass

    @abstractmethod
    def get_servo_angle(self, arm: ArmSide, joint: int) -> float:
        """Get current servo angle"""
        pass

    @abstractmethod
    def set_arm_angles(self, arm: ArmSide, angles: List[float]):
        """
        Set all servo angles for one arm
        Args:
            arm: Left or right arm
            angles: List of 4 angles for joints [0, 1, 2, 3]
        """
        pass

    @abstractmethod
    def get_arm_angles(self, arm: ArmSide) -> List[float]:
        """Get all servo angles for one arm"""
        pass

    @abstractmethod
    def move_to_home_position(self, arm: ArmSide = None):
        """
        Move arm(s) to home position
        Args:
            arm: Specific arm or None for both arms
        """
        pass

    @abstractmethod
    def move_to_preset_position(self, arm: ArmSide, preset_name: str) -> bool:
        """
        Move arm to preset position
        Args:
            arm: Left or right arm
            preset_name: Name of preset (e.g., 'wave', 'medicine_grab', 'point')
        """
        pass

    @abstractmethod
    def add_preset_position(self, preset_name: str, left_angles: List[float], right_angles: List[float]):
        """
        Add a new preset position
        Args:
            preset_name: Name of the preset
            left_angles: Angles for left arm joints
            right_angles: Angles for right arm joints
        """
        pass

    @abstractmethod
    def get_preset_positions(self) -> List[str]:
        """Get list of available preset position names"""
        pass

    @abstractmethod
    def set_movement_speed(self, speed: float):
        """Set servo movement speed (0.0 to 1.0)"""
        pass

    @abstractmethod
    def get_movement_speed(self) -> float:
        """Get current movement speed"""
        pass

    @abstractmethod
    def is_moving(self, arm: ArmSide = None) -> bool:
        """Check if arm(s) are currently moving"""
        pass

    @abstractmethod
    def emergency_stop(self):
        """Emergency stop all servo movements"""
        pass

    @abstractmethod
    def get_servo_limits(self, arm: ArmSide, joint: int) -> Tuple[float, float]:
        """Get servo angle limits as (min_angle, max_angle)"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if servo controller is connected"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get servo controller status and diagnostics"""
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown servo controller and release resources"""
        pass