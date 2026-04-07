#!/usr/bin/env python3
"""
Servo Angle Testing Script for Mars Robot
Interactive testing of individual servo angles and home position functionality
"""
import os
import sys
import time
import argparse
import threading
from typing import Dict, Any, List, Tuple

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ros2_workspace', 'src'))

try:
    from mars_hardware.hardware_manager import HardwareManager
    from mars_hardware.interfaces.arm_interface import ArmSide
except ImportError:
    print("Could not import hardware manager. Make sure you're running from the correct directory.")
    sys.exit(1)


class ServoAngleTester:
    """Interactive servo angle testing utility"""

    def __init__(self, use_mock_hardware: bool = True):
        self.use_mock_hardware = use_mock_hardware

        # Initialize hardware manager
        config = self._load_config()
        if use_mock_hardware:
            os.environ['USE_MOCK_HARDWARE'] = 'true'

        self.hardware = HardwareManager(config)

        # Current servo states
        self.current_angles = {
            'left': [0.0, 0.0, 0.0, 0.0],
            'right': [0.0, 0.0, 0.0, 0.0],
            'camera_pan': 0.0,
            'camera_tilt': 0.0
        }

        # Servo limits
        self.servo_limits = {
            'arms': [(-90, 90), (-45, 135), (-135, 45), (-90, 90)],
            'camera_pan': (-90, 90),
            'camera_tilt': (-45, 45)
        }

        # Joint names for display
        self.joint_names = [
            "Base (Joint 0)",
            "Shoulder (Joint 1)",
            "Elbow (Joint 2)",
            "Wrist (Joint 3)"
        ]

        print(f"Servo Angle Tester initialized ({'mock' if use_mock_hardware else 'real'} hardware)")

    def _load_config(self) -> Dict[str, Any]:
        """Load robot configuration"""
        try:
            import yaml
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'robot_config.yaml')
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            print(f"Warning: Could not load config: {e}. Using defaults.")
            return {}

    def initialize(self) -> bool:
        """Initialize hardware systems"""
        try:
            print("Initializing hardware systems...")

            # Initialize arms
            if not self.hardware.arms.initialize():
                print("Warning: Could not initialize arms")

            # Initialize camera servos
            if not self.hardware.camera_servos.initialize():
                print("Warning: Could not initialize camera servos")

            # Get current positions
            self.current_angles['left'] = self.hardware.arms.get_arm_angles(ArmSide.LEFT)
            self.current_angles['right'] = self.hardware.arms.get_arm_angles(ArmSide.RIGHT)
            self.current_angles['camera_pan'] = self.hardware.camera_servos.get_pan_angle()
            self.current_angles['camera_tilt'] = self.hardware.camera_servos.get_tilt_angle()

            print("Hardware initialization completed")
            return True

        except Exception as e:
            print(f"Hardware initialization failed: {e}")
            return False

    def interactive_test(self):
        """Interactive servo testing mode"""
        print("\n" + "="*80)
        print("INTERACTIVE SERVO ANGLE TESTING")
        print("="*80)
        print("Test individual servo angles for Mars Robot arms and camera")
        print("\nCommands:")
        print("  left <joint> <angle>   - Set left arm joint angle")
        print("  right <joint> <angle>  - Set right arm joint angle")
        print("  pan <angle>           - Set camera pan angle")
        print("  tilt <angle>          - Set camera tilt angle")
        print("  home                  - Move all servos to home position")
        print("  preset <name>         - Move to preset position")
        print("  status                - Show current positions")
        print("  limits                - Show servo limits")
        print("  demo                  - Run demonstration sequence")
        print("  help                  - Show this help")
        print("  quit                  - Exit tester")
        print("-"*80)

        self._show_current_status()

        while True:
            try:
                command = input("\nServo> ").strip().lower()

                if not command:
                    continue

                if command == 'quit' or command == 'exit':
                    break
                elif command == 'help':
                    self._show_help()
                elif command == 'home':
                    self._move_to_home()
                elif command == 'status':
                    self._show_current_status()
                elif command == 'limits':
                    self._show_limits()
                elif command == 'demo':
                    self._run_demo()
                elif command.startswith('left'):
                    self._handle_arm_command('left', command)
                elif command.startswith('right'):
                    self._handle_arm_command('right', command)
                elif command.startswith('pan'):
                    self._handle_camera_command('pan', command)
                elif command.startswith('tilt'):
                    self._handle_camera_command('tilt', command)
                elif command.startswith('preset'):
                    self._handle_preset_command(command)
                else:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\nExiting servo tester...")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _show_help(self):
        """Show detailed help"""
        print("\nDETAILED HELP:")
        print("="*50)
        print("Joint numbers (0-3):")
        for i, name in enumerate(self.joint_names):
            print(f"  {i}: {name}")

        print("\nExample commands:")
        print("  left 0 45       - Set left arm base to 45 degrees")
        print("  right 1 90      - Set right arm shoulder to 90 degrees")
        print("  pan -30         - Pan camera left 30 degrees")
        print("  tilt 15         - Tilt camera up 15 degrees")
        print("  preset wave     - Move to wave position")

        print("\nAvailable presets:")
        presets = self.hardware.arms.get_preset_positions()
        for preset in presets:
            print(f"  {preset}")

    def _handle_arm_command(self, arm: str, command: str):
        """Handle arm movement command"""
        try:
            parts = command.split()
            if len(parts) != 3:
                print("Usage: left/right <joint> <angle>")
                return

            joint = int(parts[1])
            angle = float(parts[2])

            if joint < 0 or joint > 3:
                print("Joint must be 0-3")
                return

            # Check limits
            min_angle, max_angle = self.servo_limits['arms'][joint]
            if angle < min_angle or angle > max_angle:
                print(f"Angle must be between {min_angle} and {max_angle} degrees")
                return

            # Move servo
            arm_side = ArmSide.LEFT if arm == 'left' else ArmSide.RIGHT
            self.hardware.arms.set_servo_angle(arm_side, joint, angle)

            # Update current state
            self.current_angles[arm][joint] = angle

            print(f"Set {arm} arm {self.joint_names[joint]} to {angle}°")

        except ValueError:
            print("Invalid joint number or angle. Use: left/right <joint> <angle>")
        except Exception as e:
            print(f"Error moving servo: {e}")

    def _handle_camera_command(self, axis: str, command: str):
        """Handle camera movement command"""
        try:
            parts = command.split()
            if len(parts) != 2:
                print(f"Usage: {axis} <angle>")
                return

            angle = float(parts[1])

            # Check limits
            if axis == 'pan':
                min_angle, max_angle = self.servo_limits['camera_pan']
            else:  # tilt
                min_angle, max_angle = self.servo_limits['camera_tilt']

            if angle < min_angle or angle > max_angle:
                print(f"Angle must be between {min_angle} and {max_angle} degrees")
                return

            # Move servo
            if axis == 'pan':
                self.hardware.camera_servos.set_pan_angle(angle)
                self.current_angles['camera_pan'] = angle
            else:  # tilt
                self.hardware.camera_servos.set_tilt_angle(angle)
                self.current_angles['camera_tilt'] = angle

            print(f"Set camera {axis} to {angle}°")

        except ValueError:
            print(f"Invalid angle. Use: {axis} <angle>")
        except Exception as e:
            print(f"Error moving camera servo: {e}")

    def _handle_preset_command(self, command: str):
        """Handle preset movement command"""
        try:
            parts = command.split()
            if len(parts) != 2:
                print("Usage: preset <name>")
                return

            preset_name = parts[1]
            available_presets = self.hardware.arms.get_preset_positions()

            if preset_name not in available_presets:
                print(f"Unknown preset: {preset_name}")
                print(f"Available presets: {', '.join(available_presets)}")
                return

            # Move to preset
            self.hardware.arms.move_to_preset_position(ArmSide.LEFT, preset_name)
            self.hardware.arms.move_to_preset_position(ArmSide.RIGHT, preset_name)

            # Update current state
            self.current_angles['left'] = self.hardware.arms.get_arm_angles(ArmSide.LEFT)
            self.current_angles['right'] = self.hardware.arms.get_arm_angles(ArmSide.RIGHT)

            print(f"Moved to preset position: {preset_name}")

        except Exception as e:
            print(f"Error moving to preset: {e}")

    def _move_to_home(self):
        """Move all servos to home position"""
        try:
            print("Moving all servos to home position...")

            # Move arms to home
            self.hardware.arms.move_to_home_position()

            # Center camera
            self.hardware.camera_servos.center_camera()

            # Update current state
            self.current_angles['left'] = [0.0, 0.0, 0.0, 0.0]
            self.current_angles['right'] = [0.0, 0.0, 0.0, 0.0]
            self.current_angles['camera_pan'] = 0.0
            self.current_angles['camera_tilt'] = 0.0

            print("All servos moved to home position")

        except Exception as e:
            print(f"Error moving to home: {e}")

    def _show_current_status(self):
        """Show current servo positions"""
        print("\nCURRENT SERVO POSITIONS:")
        print("="*50)

        # Left arm
        print("Left Arm:")
        for i, angle in enumerate(self.current_angles['left']):
            print(f"  {self.joint_names[i]}: {angle:6.1f}°")

        # Right arm
        print("\nRight Arm:")
        for i, angle in enumerate(self.current_angles['right']):
            print(f"  {self.joint_names[i]}: {angle:6.1f}°")

        # Camera
        print("\nCamera:")
        print(f"  Pan:  {self.current_angles['camera_pan']:6.1f}°")
        print(f"  Tilt: {self.current_angles['camera_tilt']:6.1f}°")

    def _show_limits(self):
        """Show servo angle limits"""
        print("\nSERVO ANGLE LIMITS:")
        print("="*50)

        print("Arm Joints:")
        for i, (min_angle, max_angle) in enumerate(self.servo_limits['arms']):
            print(f"  {self.joint_names[i]}: {min_angle:4.0f}° to {max_angle:4.0f}°")

        min_pan, max_pan = self.servo_limits['camera_pan']
        min_tilt, max_tilt = self.servo_limits['camera_tilt']
        print(f"\nCamera:")
        print(f"  Pan:  {min_pan:4.0f}° to {max_pan:4.0f}°")
        print(f"  Tilt: {min_tilt:4.0f}° to {max_tilt:4.0f}°")

    def _run_demo(self):
        """Run servo demonstration sequence"""
        print("\nRunning servo demonstration...")
        print("This will move all servos through a test sequence")

        try:
            # Demo sequence
            demo_steps = [
                ("Home position", lambda: self._move_to_home()),
                ("Wave gesture", lambda: self._demo_wave()),
                ("Camera scan", lambda: self._demo_camera_scan()),
                ("Arm movements", lambda: self._demo_arm_movements()),
                ("Return to home", lambda: self._move_to_home())
            ]

            for step_name, step_func in demo_steps:
                print(f"\n→ {step_name}")
                step_func()
                time.sleep(2)  # Pause between steps

            print("\nDemonstration completed!")

        except Exception as e:
            print(f"Error during demonstration: {e}")

    def _demo_wave(self):
        """Demonstrate wave gesture"""
        try:
            # Move to wave preset if available
            presets = self.hardware.arms.get_preset_positions()
            if 'wave' in presets:
                self.hardware.arms.move_to_preset_position(ArmSide.RIGHT, 'wave')
            else:
                # Manual wave motion
                self.hardware.arms.set_servo_angle(ArmSide.RIGHT, 1, 60)  # Shoulder up
                self.hardware.arms.set_servo_angle(ArmSide.RIGHT, 2, -30)  # Elbow bend
                time.sleep(1)

                # Wave motion
                for _ in range(3):
                    self.hardware.arms.set_servo_angle(ArmSide.RIGHT, 3, -45)  # Wrist left
                    time.sleep(0.5)
                    self.hardware.arms.set_servo_angle(ArmSide.RIGHT, 3, 45)   # Wrist right
                    time.sleep(0.5)

            self.hardware.arms.set_servo_angle(ArmSide.RIGHT, 3, 0)  # Center wrist

        except Exception as e:
            print(f"Wave demo error: {e}")

    def _demo_camera_scan(self):
        """Demonstrate camera scanning"""
        try:
            # Horizontal scan
            scan_angles = [-60, -30, 0, 30, 60, 0]
            for angle in scan_angles:
                self.hardware.camera_servos.set_pan_angle(angle)
                time.sleep(0.5)

            # Vertical scan
            tilt_angles = [-30, -15, 0, 15, 30, 0]
            for angle in tilt_angles:
                self.hardware.camera_servos.set_tilt_angle(angle)
                time.sleep(0.5)

        except Exception as e:
            print(f"Camera scan demo error: {e}")

    def _demo_arm_movements(self):
        """Demonstrate various arm movements"""
        try:
            movements = [
                (ArmSide.LEFT, 0, 45),   # Left base
                (ArmSide.RIGHT, 0, -45), # Right base
                (ArmSide.LEFT, 1, 90),   # Left shoulder
                (ArmSide.RIGHT, 1, 90),  # Right shoulder
                (ArmSide.LEFT, 2, -90),  # Left elbow
                (ArmSide.RIGHT, 2, -90), # Right elbow
            ]

            for arm, joint, angle in movements:
                self.hardware.arms.set_servo_angle(arm, joint, angle)
                time.sleep(0.8)

        except Exception as e:
            print(f"Arm movement demo error: {e}")

    def batch_test(self, test_file: str):
        """Run batch test from file"""
        try:
            print(f"Running batch test from: {test_file}")

            with open(test_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        print(f"Line {line_num}: {line}")
                        self._execute_command(line)
                        time.sleep(0.5)  # Brief pause between commands

        except FileNotFoundError:
            print(f"Test file not found: {test_file}")
        except Exception as e:
            print(f"Error running batch test: {e}")

    def _execute_command(self, command: str):
        """Execute a single command (for batch mode)"""
        command = command.strip().lower()

        if command == 'home':
            self._move_to_home()
        elif command.startswith('left'):
            self._handle_arm_command('left', command)
        elif command.startswith('right'):
            self._handle_arm_command('right', command)
        elif command.startswith('pan'):
            self._handle_camera_command('pan', command)
        elif command.startswith('tilt'):
            self._handle_camera_command('tilt', command)
        elif command.startswith('preset'):
            self._handle_preset_command(command)
        else:
            print(f"Unknown command in batch file: {command}")

    def cleanup(self):
        """Cleanup hardware resources"""
        try:
            print("Moving servos to safe position...")
            self._move_to_home()
            self.hardware.shutdown()
            print("Servo testing cleanup completed")
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test servo angles for Mars Robot')
    parser.add_argument('--mode', choices=['interactive', 'demo', 'batch'], default='interactive',
                       help='Testing mode (default: interactive)')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock hardware for testing')
    parser.add_argument('--batch-file', help='Batch test file for batch mode')

    args = parser.parse_args()

    # Create tester
    tester = ServoAngleTester(use_mock_hardware=args.mock)

    # Initialize hardware
    if not tester.initialize():
        print("Failed to initialize hardware")
        sys.exit(1)

    try:
        if args.mode == 'interactive':
            tester.interactive_test()
        elif args.mode == 'demo':
            tester._run_demo()
        elif args.mode == 'batch':
            if not args.batch_file:
                print("Batch mode requires --batch-file argument")
                sys.exit(1)
            tester.batch_test(args.batch_file)

    except Exception as e:
        print(f"Error during servo testing: {e}")
    finally:
        tester.cleanup()


if __name__ == '__main__':
    main()