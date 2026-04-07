"""
Mock Camera Servos Implementation for Development
"""
from typing import Tuple, Dict, Any
import time
import math

from ..interfaces.camera_servo_interface import CameraServoInterface


class MockCameraServos(CameraServoInterface):
    """Mock camera pan/tilt servo implementation"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Current servo positions
        self.pan_angle = 0.0  # Current pan angle
        self.tilt_angle = 0.0  # Current tilt angle

        # Servo limits from config or defaults
        self.pan_limits = self.config.get('pan_servo', {}).get('range', [-90, 90])
        self.tilt_limits = self.config.get('tilt_servo', {}).get('range', [-45, 45])

        # Movement settings
        self.movement_speed = 0.5  # 0.0 to 1.0
        self.is_moving_flag = False

        # Target positions for smooth movement simulation
        self.target_pan = 0.0
        self.target_tilt = 0.0

        self.is_initialized = False

    def initialize(self) -> bool:
        """Initialize camera servo hardware"""
        self.is_initialized = True
        print("Mock camera servos initialized")
        print(f"Pan servo pin: {self.config.get('pan_servo', {}).get('pin', 'N/A')}")
        print(f"Tilt servo pin: {self.config.get('tilt_servo', {}).get('pin', 'N/A')}")
        print(f"Pan limits: {self.pan_limits}")
        print(f"Tilt limits: {self.tilt_limits}")
        return True

    def set_pan_angle(self, angle: float):
        """Set pan angle"""
        # Apply limits
        angle = max(self.pan_limits[0], min(self.pan_limits[1], angle))
        self.pan_angle = angle
        self.target_pan = angle
        print(f"Mock camera pan set to {angle:.1f}°")

    def set_tilt_angle(self, angle: float):
        """Set tilt angle"""
        # Apply limits
        angle = max(self.tilt_limits[0], min(self.tilt_limits[1], angle))
        self.tilt_angle = angle
        self.target_tilt = angle
        print(f"Mock camera tilt set to {angle:.1f}°")

    def get_pan_angle(self) -> float:
        """Get current pan angle"""
        return self.pan_angle

    def get_tilt_angle(self) -> float:
        """Get current tilt angle"""
        return self.tilt_angle

    def set_pan_tilt(self, pan: float, tilt: float):
        """Set both pan and tilt angles simultaneously"""
        self.set_pan_angle(pan)
        self.set_tilt_angle(tilt)

    def get_pan_tilt(self) -> Tuple[float, float]:
        """Get current pan and tilt angles"""
        return (self.pan_angle, self.tilt_angle)

    def center_camera(self):
        """Move camera to center position"""
        self.set_pan_tilt(0.0, 0.0)
        print("Mock camera centered")

    def look_left(self, angle: float = 45.0):
        """Look left by specified angle"""
        self.set_pan_angle(angle)

    def look_right(self, angle: float = 45.0):
        """Look right by specified angle"""
        self.set_pan_angle(-angle)

    def look_up(self, angle: float = 30.0):
        """Look up by specified angle"""
        self.set_tilt_angle(angle)

    def look_down(self, angle: float = 30.0):
        """Look down by specified angle"""
        self.set_tilt_angle(-angle)

    def scan_area(self, scan_pattern: str = "horizontal"):
        """Perform scanning motion"""
        print(f"Starting mock camera scan: {scan_pattern}")

        if scan_pattern == "horizontal":
            positions = [
                (-60, 0), (-30, 0), (0, 0), (30, 0), (60, 0), (0, 0)
            ]
        elif scan_pattern == "vertical":
            positions = [
                (0, -30), (0, -15), (0, 0), (0, 15), (0, 30), (0, 0)
            ]
        elif scan_pattern == "grid":
            positions = [
                (-45, -30), (0, -30), (45, -30),
                (-45, 0), (0, 0), (45, 0),
                (-45, 30), (0, 30), (45, 30),
                (0, 0)
            ]
        else:
            print(f"Unknown scan pattern: {scan_pattern}")
            return

        for pan, tilt in positions:
            self.set_pan_tilt(pan, tilt)
            time.sleep(0.5 / self.movement_speed)  # Simulate movement time

        print(f"Mock camera scan '{scan_pattern}' completed")

    def follow_target(self, target_x: float, target_y: float, image_width: int, image_height: int):
        """Calculate pan/tilt to follow target in camera frame"""
        # Calculate center offset
        center_x = image_width / 2
        center_y = image_height / 2

        # Calculate offset from center
        offset_x = target_x - center_x
        offset_y = target_y - center_y

        # Convert pixel offset to angle (simple proportional control)
        # Assume 60° field of view horizontally, 45° vertically
        fov_horizontal = 60.0
        fov_vertical = 45.0

        pan_adjustment = (offset_x / center_x) * (fov_horizontal / 2)
        tilt_adjustment = -(offset_y / center_y) * (fov_vertical / 2)  # Invert Y

        # Apply proportional control
        gain = 0.5  # Adjust responsiveness
        new_pan = self.pan_angle + (pan_adjustment * gain)
        new_tilt = self.tilt_angle + (tilt_adjustment * gain)

        self.set_pan_tilt(new_pan, new_tilt)
        print(f"Mock camera following target: ({target_x}, {target_y}) -> Pan={new_pan:.1f}°, Tilt={new_tilt:.1f}°")

    def set_movement_speed(self, speed: float):
        """Set servo movement speed"""
        self.movement_speed = max(0.0, min(1.0, speed))
        print(f"Mock camera servo speed set to {self.movement_speed:.2f}")

    def get_movement_speed(self) -> float:
        """Get current movement speed"""
        return self.movement_speed

    def is_moving(self) -> bool:
        """Check if servos are currently moving"""
        # For mock, assume movement is instantaneous
        return False

    def stop(self):
        """Stop servo movement immediately"""
        print("Mock camera servos stopped")

    def get_limits(self) -> Dict[str, Tuple[float, float]]:
        """Get servo angle limits"""
        return {
            'pan': tuple(self.pan_limits),
            'tilt': tuple(self.tilt_limits)
        }

    def is_connected(self) -> bool:
        """Check if servo controller is connected"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get servo status and diagnostics"""
        return {
            'connected': self.is_connected(),
            'initialized': self.is_initialized,
            'current_position': {
                'pan': self.pan_angle,
                'tilt': self.tilt_angle
            },
            'limits': {
                'pan': self.pan_limits,
                'tilt': self.tilt_limits
            },
            'movement_speed': self.movement_speed,
            'servo_config': {
                'pan_servo': self.config.get('pan_servo', {}),
                'tilt_servo': self.config.get('tilt_servo', {})
            }
        }

    def demonstrate_movement(self):
        """Demonstrate camera servo movements for testing"""
        print("Starting mock camera servo demonstration...")

        movements = [
            ("Center", 0, 0),
            ("Look Left", 60, 0),
            ("Look Right", -60, 0),
            ("Look Up", 0, 30),
            ("Look Down", 0, -30),
            ("Upper Left", 45, 25),
            ("Lower Right", -45, -25),
            ("Center", 0, 0)
        ]

        for description, pan, tilt in movements:
            print(f"  {description}: Pan={pan}°, Tilt={tilt}°")
            self.set_pan_tilt(pan, tilt)
            time.sleep(0.8 / self.movement_speed)

        print("Mock camera servo demonstration completed")

    def shutdown(self):
        """Shutdown servo controller"""
        self.center_camera()
        self.is_initialized = False
        print("Mock camera servos shutdown completed")