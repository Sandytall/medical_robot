"""
Mock Arms Implementation for Development
"""
from typing import List, Dict, Any, Tuple
import time
import json

from ..interfaces.arm_interface import ArmInterface, ArmSide


class MockArms(ArmInterface):
    """Mock robotic arms implementation (2 arms × 4 servos each)"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Servo angles for each arm (4 servos per arm)
        self.left_angles = [0.0, 0.0, 0.0, 0.0]
        self.right_angles = [0.0, 0.0, 0.0, 0.0]

        # Servo limits (min, max) for each joint
        self.servo_limits = [
            (-90.0, 90.0),   # Joint 0: Base rotation
            (-45.0, 135.0),  # Joint 1: Shoulder
            (-135.0, 45.0),  # Joint 2: Elbow
            (-90.0, 90.0)    # Joint 3: Wrist
        ]

        # Movement settings
        self.movement_speed = 0.5  # 0.0 to 1.0
        self.is_moving = False
        self.target_angles = {'left': self.left_angles.copy(), 'right': self.right_angles.copy()}

        # Preset positions
        self.preset_positions = {
            'home': {
                'left': [0.0, 0.0, 0.0, 0.0],
                'right': [0.0, 0.0, 0.0, 0.0]
            },
            'wave': {
                'left': [0.0, 45.0, -45.0, 0.0],
                'right': [0.0, 45.0, -45.0, 0.0]
            },
            'medicine_grab': {
                'left': [45.0, 90.0, -90.0, 0.0],
                'right': [-45.0, 90.0, -90.0, 0.0]
            },
            'point_forward': {
                'left': [0.0, 0.0, 0.0, 0.0],
                'right': [0.0, 90.0, 0.0, 0.0]
            },
            'greet': {
                'left': [-30.0, 60.0, -30.0, 0.0],
                'right': [30.0, 60.0, -30.0, 0.0]
            }
        }

        self.is_initialized = False

    def initialize(self) -> bool:
        """Initialize all servo motors"""
        self.is_initialized = True
        print("Mock robotic arms initialized")
        print(f"Left arm servos: {self.config.get('left_arm', {}).get('servos', [])}")
        print(f"Right arm servos: {self.config.get('right_arm', {}).get('servos', [])}")
        print(f"Available presets: {list(self.preset_positions.keys())}")
        return True

    def set_servo_angle(self, arm: ArmSide, joint: int, angle: float):
        """Set individual servo angle"""
        if not self.is_initialized:
            print("Servo controller not initialized")
            return

        if joint < 0 or joint > 3:
            print(f"Invalid joint number: {joint}. Must be 0-3")
            return

        # Apply servo limits
        min_angle, max_angle = self.servo_limits[joint]
        angle = max(min_angle, min(max_angle, angle))

        if arm == ArmSide.LEFT:
            self.left_angles[joint] = angle
        else:
            self.right_angles[joint] = angle

        print(f"Mock servo {arm.value} arm joint {joint} set to {angle:.1f}°")

    def get_servo_angle(self, arm: ArmSide, joint: int) -> float:
        """Get current servo angle"""
        if joint < 0 or joint > 3:
            return 0.0

        if arm == ArmSide.LEFT:
            return self.left_angles[joint]
        else:
            return self.right_angles[joint]

    def set_arm_angles(self, arm: ArmSide, angles: List[float]):
        """Set all servo angles for one arm"""
        if len(angles) != 4:
            print(f"Invalid number of angles: {len(angles)}. Expected 4")
            return

        for joint, angle in enumerate(angles):
            self.set_servo_angle(arm, joint, angle)

        print(f"Mock {arm.value} arm angles set: {angles}")

    def get_arm_angles(self, arm: ArmSide) -> List[float]:
        """Get all servo angles for one arm"""
        if arm == ArmSide.LEFT:
            return self.left_angles.copy()
        else:
            return self.right_angles.copy()

    def move_to_home_position(self, arm: ArmSide = None):
        """Move arm(s) to home position"""
        home_preset = self.preset_positions['home']

        if arm is None:
            # Move both arms
            self.set_arm_angles(ArmSide.LEFT, home_preset['left'])
            self.set_arm_angles(ArmSide.RIGHT, home_preset['right'])
            print("Mock arms moved to home position (both arms)")
        else:
            self.set_arm_angles(arm, home_preset[arm.value])
            print(f"Mock {arm.value} arm moved to home position")

    def move_to_preset_position(self, arm: ArmSide, preset_name: str) -> bool:
        """Move arm to preset position"""
        if preset_name not in self.preset_positions:
            print(f"Unknown preset: {preset_name}")
            return False

        preset = self.preset_positions[preset_name]
        self.set_arm_angles(arm, preset[arm.value])
        print(f"Mock {arm.value} arm moved to preset '{preset_name}'")
        return True

    def add_preset_position(self, preset_name: str, left_angles: List[float], right_angles: List[float]):
        """Add a new preset position"""
        if len(left_angles) != 4 or len(right_angles) != 4:
            print("Invalid preset angles. Each arm must have 4 angles")
            return

        self.preset_positions[preset_name] = {
            'left': left_angles.copy(),
            'right': right_angles.copy()
        }
        print(f"Added new preset '{preset_name}': Left={left_angles}, Right={right_angles}")

    def get_preset_positions(self) -> List[str]:
        """Get list of available preset position names"""
        return list(self.preset_positions.keys())

    def set_movement_speed(self, speed: float):
        """Set servo movement speed"""
        self.movement_speed = max(0.0, min(1.0, speed))
        print(f"Mock servo movement speed set to {self.movement_speed:.2f}")

    def get_movement_speed(self) -> float:
        """Get current movement speed"""
        return self.movement_speed

    def is_moving(self, arm: ArmSide = None) -> bool:
        """Check if arm(s) are currently moving"""
        # For mock implementation, assume movement is instantaneous
        return False

    def emergency_stop(self):
        """Emergency stop all servo movements"""
        print("Mock arms EMERGENCY STOP activated")
        # In real implementation, this would immediately halt all servo movements

    def get_servo_limits(self, arm: ArmSide, joint: int) -> Tuple[float, float]:
        """Get servo angle limits"""
        if joint < 0 or joint > 3:
            return (0.0, 0.0)
        return self.servo_limits[joint]

    def is_connected(self) -> bool:
        """Check if servo controller is connected"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get servo controller status and diagnostics"""
        return {
            'connected': self.is_connected(),
            'initialized': self.is_initialized,
            'movement_speed': self.movement_speed,
            'current_angles': {
                'left': self.left_angles.copy(),
                'right': self.right_angles.copy()
            },
            'servo_limits': self.servo_limits,
            'available_presets': list(self.preset_positions.keys()),
            'servo_config': {
                'left_arm': self.config.get('left_arm', {}),
                'right_arm': self.config.get('right_arm', {})
            }
        }

    def save_current_as_preset(self, preset_name: str):
        """Save current arm positions as a new preset"""
        self.add_preset_position(preset_name, self.left_angles.copy(), self.right_angles.copy())

    def demonstrate_movement(self):
        """Demonstrate arm movements for testing"""
        print("Starting mock arm movement demonstration...")

        movements = [
            ("wave", "Waving motion"),
            ("medicine_grab", "Medicine grabbing position"),
            ("point_forward", "Pointing forward"),
            ("greet", "Greeting position"),
            ("home", "Return to home")
        ]

        for preset, description in movements:
            print(f"  {description}...")
            self.move_to_preset_position(ArmSide.LEFT, preset)
            self.move_to_preset_position(ArmSide.RIGHT, preset)
            time.sleep(1)  # Simulate movement time

        print("Mock arm demonstration completed")

    def shutdown(self):
        """Shutdown servo controller"""
        self.move_to_home_position()
        self.is_initialized = False
        print("Mock robotic arms shutdown completed")