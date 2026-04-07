"""
Camera Servo Interface for Pan/Tilt Control
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any


class CameraServoInterface(ABC):
    """Abstract interface for camera pan/tilt servo control"""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize camera servo hardware"""
        pass

    @abstractmethod
    def set_pan_angle(self, angle: float):
        """
        Set pan angle
        Args:
            angle: Pan angle in degrees (-90 to +90)
        """
        pass

    @abstractmethod
    def set_tilt_angle(self, angle: float):
        """
        Set tilt angle
        Args:
            angle: Tilt angle in degrees (-45 to +45)
        """
        pass

    @abstractmethod
    def get_pan_angle(self) -> float:
        """Get current pan angle"""
        pass

    @abstractmethod
    def get_tilt_angle(self) -> float:
        """Get current tilt angle"""
        pass

    @abstractmethod
    def set_pan_tilt(self, pan: float, tilt: float):
        """
        Set both pan and tilt angles simultaneously
        Args:
            pan: Pan angle in degrees (-90 to +90)
            tilt: Tilt angle in degrees (-45 to +45)
        """
        pass

    @abstractmethod
    def get_pan_tilt(self) -> Tuple[float, float]:
        """Get current pan and tilt angles as (pan, tilt)"""
        pass

    @abstractmethod
    def center_camera(self):
        """Move camera to center position (0, 0)"""
        pass

    @abstractmethod
    def look_left(self, angle: float = 45.0):
        """Look left by specified angle"""
        pass

    @abstractmethod
    def look_right(self, angle: float = 45.0):
        """Look right by specified angle"""
        pass

    @abstractmethod
    def look_up(self, angle: float = 30.0):
        """Look up by specified angle"""
        pass

    @abstractmethod
    def look_down(self, angle: float = 30.0):
        """Look down by specified angle"""
        pass

    @abstractmethod
    def scan_area(self, scan_pattern: str = "horizontal"):
        """
        Perform scanning motion
        Args:
            scan_pattern: 'horizontal', 'vertical', or 'grid'
        """
        pass

    @abstractmethod
    def follow_target(self, target_x: float, target_y: float, image_width: int, image_height: int):
        """
        Calculate pan/tilt to follow target in camera frame
        Args:
            target_x: Target X coordinate in pixels
            target_y: Target Y coordinate in pixels
            image_width: Camera image width
            image_height: Camera image height
        """
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
    def is_moving(self) -> bool:
        """Check if servos are currently moving"""
        pass

    @abstractmethod
    def stop(self):
        """Stop servo movement immediately"""
        pass

    @abstractmethod
    def get_limits(self) -> Dict[str, Tuple[float, float]]:
        """Get servo angle limits as {'pan': (min, max), 'tilt': (min, max)}"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if servo controller is connected"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get servo status and diagnostics"""
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown servo controller and release resources"""
        pass