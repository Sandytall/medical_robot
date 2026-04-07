#!/usr/bin/env python3
"""
Comprehensive Hardware Testing Script for Mars Robot
Tests all hardware components including camera, motors, servos, audio, and display
"""
import os
import sys
import time
import argparse
import json
import threading
from typing import Dict, Any, List, Tuple

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ros2_workspace', 'src'))

try:
    from mars_hardware.hardware_manager import HardwareManager
    from mars_hardware.interfaces.arm_interface import ArmSide
    from mars_hardware.interfaces.display_interface import EmotionType
except ImportError:
    print("Could not import hardware manager. Make sure you're running from the correct directory.")
    sys.exit(1)


class HardwareTester:
    """Comprehensive hardware testing utility"""

    def __init__(self, use_mock_hardware: bool = True):
        self.use_mock_hardware = use_mock_hardware
        self.test_results = {}
        self.running = False

        # Initialize hardware manager
        config = self._load_config()
        if use_mock_hardware:
            os.environ['USE_MOCK_HARDWARE'] = 'true'

        self.hardware = HardwareManager(config)
        print(f"Hardware Tester initialized ({'mock' if use_mock_hardware else 'real'} hardware)")

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

    def run_all_tests(self) -> bool:
        """Run comprehensive tests on all hardware components"""
        print("\n" + "="*80)
        print("MARS ROBOT COMPREHENSIVE HARDWARE TESTING")
        print("="*80)
        print("Testing all hardware components...")

        all_tests_passed = True

        # Test sequence
        test_sequence = [
            ("System Information", self._test_system_info),
            ("Camera System", self._test_camera),
            ("Motor System", self._test_motors),
            ("Arm Servos", self._test_arms),
            ("Camera Servos", self._test_camera_servos),
            ("Audio System", self._test_audio),
            ("Display System", self._test_display),
            ("Emergency Stop", self._test_emergency_stop)
        ]

        for test_name, test_function in test_sequence:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_function()
                self.test_results[test_name] = result

                if result:
                    print(f"✓ {test_name} PASSED")
                else:
                    print(f"✗ {test_name} FAILED")
                    all_tests_passed = False

            except Exception as e:
                print(f"✗ {test_name} ERROR: {e}")
                self.test_results[test_name] = False
                all_tests_passed = False

            time.sleep(1)  # Brief pause between tests

        # Print summary
        self._print_test_summary()

        return all_tests_passed

    def _test_system_info(self) -> bool:
        """Test system information and detection"""
        try:
            system_info = self.hardware.get_system_info()

            print("System Information:")
            print(f"  Platform: {system_info.get('platform', 'Unknown')}")
            print(f"  Architecture: {system_info.get('architecture', 'Unknown')}")
            print(f"  Is Pi: {system_info.get('is_pi', False)}")
            print(f"  Using Real Hardware: {system_info.get('using_real_hardware', False)}")

            print("\nHardware Status:")
            hardware_status = system_info.get('hardware_status', {})
            for component, status in hardware_status.items():
                status_icon = "✓" if status else "✗"
                print(f"  {status_icon} {component}: {'Connected' if status else 'Not connected'}")

            return True

        except Exception as e:
            print(f"System info test error: {e}")
            return False

    def _test_camera(self) -> bool:
        """Test camera functionality"""
        try:
            print("Testing camera initialization...")
            if not self.hardware.camera.initialize():
                print("Camera initialization failed")
                return False

            print("✓ Camera initialized")

            # Test resolution settings
            print("Testing resolution settings...")
            resolutions = [(640, 480), (320, 240), (800, 600)]

            for width, height in resolutions:
                if self.hardware.camera.set_resolution(width, height):
                    current_res = self.hardware.camera.get_resolution()
                    print(f"✓ Resolution {width}x{height}: Set to {current_res[0]}x{current_res[1]}")
                else:
                    print(f"✗ Could not set resolution {width}x{height}")

            # Test frame capture
            print("Testing frame capture...")
            for i in range(3):
                frame = self.hardware.camera.capture_frame()
                if frame is not None:
                    print(f"✓ Frame {i+1} captured: {frame.shape if hasattr(frame, 'shape') else 'Valid frame'}")
                else:
                    print(f"✗ Frame {i+1} capture failed")
                    return False
                time.sleep(0.5)

            # Test streaming
            print("Testing video streaming...")
            if self.hardware.camera.start_streaming():
                print("✓ Streaming started")
                time.sleep(2)

                if self.hardware.camera.is_streaming():
                    print("✓ Streaming active")
                else:
                    print("✗ Streaming not active")

                self.hardware.camera.stop_streaming()
                print("✓ Streaming stopped")
            else:
                print("✗ Could not start streaming")
                return False

            # Get camera info
            camera_info = self.hardware.camera.get_camera_info()
            print(f"Camera info: {camera_info.get('camera_model', 'Unknown model')}")

            return True

        except Exception as e:
            print(f"Camera test error: {e}")
            return False

    def _test_motors(self) -> bool:
        """Test motor functionality"""
        try:
            print("Testing motor initialization...")
            if not self.hardware.motors.initialize():
                print("Motor initialization failed")
                return False

            print("✓ Motors initialized")

            # Test individual motor control
            print("Testing individual motor control...")
            test_speeds = [
                (25.0, 25.0),   # Forward slow
                (-25.0, -25.0), # Backward slow
                (25.0, -25.0),  # Turn right
                (-25.0, 25.0),  # Turn left
                (0.0, 0.0)      # Stop
            ]

            for left_speed, right_speed in test_speeds:
                print(f"Setting motors: Left={left_speed}%, Right={right_speed}%")
                self.hardware.motors.set_motor_speed(left_speed, right_speed)

                # Check if speeds were set
                current_speeds = self.hardware.motors.get_motor_speeds()
                print(f"  Current speeds: Left={current_speeds[0]:.1f}%, Right={current_speeds[1]:.1f}%")

                time.sleep(1)

            # Test movement functions
            print("Testing movement functions...")
            movements = [
                ("forward", lambda: self.hardware.motors.move_forward(30.0)),
                ("backward", lambda: self.hardware.motors.move_backward(30.0)),
                ("turn left", lambda: self.hardware.motors.turn_left(30.0)),
                ("turn right", lambda: self.hardware.motors.turn_right(30.0)),
                ("stop", lambda: self.hardware.motors.stop())
            ]

            for movement_name, movement_func in movements:
                print(f"Testing {movement_name}...")
                movement_func()
                time.sleep(0.5)

            # Test speed limits
            print("Testing speed limits...")
            original_limit = self.hardware.motors.get_speed_limit()

            self.hardware.motors.set_speed_limit(50.0)
            if abs(self.hardware.motors.get_speed_limit() - 50.0) < 0.1:
                print("✓ Speed limit setting works")
            else:
                print("✗ Speed limit setting failed")

            self.hardware.motors.set_speed_limit(original_limit)

            # Get motor status
            motor_status = self.hardware.motors.get_status()
            print(f"Motor status: Connected={motor_status.get('connected', False)}")

            return True

        except Exception as e:
            print(f"Motor test error: {e}")
            return False

    def _test_arms(self) -> bool:
        """Test robotic arm functionality"""
        try:
            print("Testing arm initialization...")
            if not self.hardware.arms.initialize():
                print("Arm initialization failed")
                return False

            print("✓ Arms initialized")

            # Test individual servo control
            print("Testing individual servo control...")
            test_angles = [0, 45, -45, 0]  # Test sequence for each joint

            for arm_side in [ArmSide.LEFT, ArmSide.RIGHT]:
                arm_name = arm_side.value
                print(f"Testing {arm_name} arm...")

                for joint in range(4):
                    for angle in test_angles:
                        # Check limits
                        limits = self.hardware.arms.get_servo_limits(arm_side, joint)
                        if limits[0] <= angle <= limits[1]:
                            print(f"  Setting {arm_name} joint {joint} to {angle}°")
                            self.hardware.arms.set_servo_angle(arm_side, joint, angle)

                            # Verify angle was set
                            current_angle = self.hardware.arms.get_servo_angle(arm_side, joint)
                            print(f"    Current angle: {current_angle:.1f}°")

                        time.sleep(0.3)

            # Test preset positions
            print("Testing preset positions...")
            presets = self.hardware.arms.get_preset_positions()
            print(f"Available presets: {', '.join(presets)}")

            for preset in presets[:3]:  # Test first 3 presets
                print(f"Testing preset: {preset}")
                success_left = self.hardware.arms.move_to_preset_position(ArmSide.LEFT, preset)
                success_right = self.hardware.arms.move_to_preset_position(ArmSide.RIGHT, preset)

                if success_left and success_right:
                    print(f"✓ Preset {preset} successful")
                else:
                    print(f"✗ Preset {preset} failed")

                time.sleep(1)

            # Test home position
            print("Testing home position...")
            self.hardware.arms.move_to_home_position()
            print("✓ Moved to home position")

            # Test movement speed
            print("Testing movement speed control...")
            original_speed = self.hardware.arms.get_movement_speed()

            for speed in [0.2, 0.8, original_speed]:
                self.hardware.arms.set_movement_speed(speed)
                current_speed = self.hardware.arms.get_movement_speed()
                print(f"Speed set to {speed:.1f}, current: {current_speed:.1f}")

            # Get arm status
            arm_status = self.hardware.arms.get_status()
            print(f"Arm status: Connected={arm_status.get('connected', False)}")

            return True

        except Exception as e:
            print(f"Arm test error: {e}")
            return False

    def _test_camera_servos(self) -> bool:
        """Test camera servo functionality"""
        try:
            print("Testing camera servo initialization...")
            if not self.hardware.camera_servos.initialize():
                print("Camera servo initialization failed")
                return False

            print("✓ Camera servos initialized")

            # Test pan control
            print("Testing pan control...")
            pan_angles = [-45, 0, 45, 0]
            for angle in pan_angles:
                print(f"Setting pan to {angle}°")
                self.hardware.camera_servos.set_pan_angle(angle)
                current_pan = self.hardware.camera_servos.get_pan_angle()
                print(f"  Current pan: {current_pan:.1f}°")
                time.sleep(0.5)

            # Test tilt control
            print("Testing tilt control...")
            tilt_angles = [-30, 0, 30, 0]
            for angle in tilt_angles:
                print(f"Setting tilt to {angle}°")
                self.hardware.camera_servos.set_tilt_angle(angle)
                current_tilt = self.hardware.camera_servos.get_tilt_angle()
                print(f"  Current tilt: {current_tilt:.1f}°")
                time.sleep(0.5)

            # Test combined movements
            print("Testing combined pan/tilt movements...")
            positions = [(45, 20), (-45, -20), (0, 0)]
            for pan, tilt in positions:
                print(f"Setting pan/tilt to ({pan}°, {tilt}°)")
                self.hardware.camera_servos.set_pan_tilt(pan, tilt)
                current_pos = self.hardware.camera_servos.get_pan_tilt()
                print(f"  Current position: ({current_pos[0]:.1f}°, {current_pos[1]:.1f}°)")
                time.sleep(0.7)

            # Test center position
            print("Testing center position...")
            self.hardware.camera_servos.center_camera()
            center_pos = self.hardware.camera_servos.get_pan_tilt()
            print(f"Center position: ({center_pos[0]:.1f}°, {center_pos[1]:.1f}°)")

            # Test scan patterns
            print("Testing scan patterns...")
            self.hardware.camera_servos.scan_area("horizontal")
            time.sleep(1)

            # Get servo status
            servo_status = self.hardware.camera_servos.get_status()
            print(f"Camera servo status: Connected={servo_status.get('connected', False)}")

            return True

        except Exception as e:
            print(f"Camera servo test error: {e}")
            return False

    def _test_audio(self) -> bool:
        """Test audio system functionality"""
        try:
            print("Testing audio initialization...")
            if not self.hardware.audio.initialize():
                print("Audio initialization failed")
                return False

            print("✓ Audio initialized")

            # Test volume control
            print("Testing volume control...")
            original_volume = self.hardware.audio.get_volume()

            for volume in [0.3, 0.7, 1.0]:
                self.hardware.audio.set_volume(volume)
                current_volume = self.hardware.audio.get_volume()
                print(f"Volume set to {volume:.1f}, current: {current_volume:.1f}")

            self.hardware.audio.set_volume(original_volume)

            # Test mute/unmute
            print("Testing mute functionality...")
            self.hardware.audio.mute()
            print(f"Muted: {self.hardware.audio.is_muted()}")

            self.hardware.audio.unmute()
            print(f"Muted after unmute: {self.hardware.audio.is_muted()}")

            # Test text-to-speech
            print("Testing text-to-speech...")
            test_phrases = [
                "Hello, I am MARS robot",
                "Audio system test successful",
                "Voice synthesis working properly"
            ]

            for phrase in test_phrases:
                print(f"Speaking: '{phrase}'")
                success = self.hardware.audio.play_text(phrase)
                print(f"  TTS result: {'Success' if success else 'Failed'}")
                time.sleep(0.5)

            # Test sound effects
            print("Testing sound effects...")
            effects = ['beep', 'success', 'alert']

            for effect in effects:
                print(f"Playing sound effect: {effect}")
                success = self.hardware.audio.play_sound_effect(effect)
                print(f"  Effect result: {'Success' if success else 'Failed'}")
                time.sleep(0.5)

            # Test microphone
            print("Testing microphone...")
            original_gain = self.hardware.audio.get_microphone_gain()

            self.hardware.audio.set_microphone_gain(0.7)
            current_gain = self.hardware.audio.get_microphone_gain()
            print(f"Microphone gain: {current_gain:.1f}")

            # Test recording
            print("Testing audio recording (2 seconds)...")
            recorded_audio = self.hardware.audio.record_audio(2.0)
            if recorded_audio is not None:
                print(f"✓ Recording successful: {len(recorded_audio) if hasattr(recorded_audio, '__len__') else 'Valid data'}")
            else:
                print("✗ Recording failed")

            self.hardware.audio.set_microphone_gain(original_gain)

            # Test audio devices
            print("Testing audio device enumeration...")
            devices = self.hardware.audio.get_audio_devices()
            print(f"Input devices: {len(devices.get('input', []))}")
            print(f"Output devices: {len(devices.get('output', []))}")

            # Test audio functionality
            audio_test = self.hardware.audio.test_audio()
            print(f"Audio test results: {audio_test}")

            return True

        except Exception as e:
            print(f"Audio test error: {e}")
            return False

    def _test_display(self) -> bool:
        """Test display functionality"""
        try:
            print("Testing display initialization...")
            if not self.hardware.display.initialize():
                print("Display initialization failed")
                return False

            print("✓ Display initialized")

            # Test emotions
            print("Testing emotion display...")
            emotions = [EmotionType.HAPPY, EmotionType.THINKING, EmotionType.NEUTRAL]

            for emotion in emotions:
                print(f"Displaying emotion: {emotion.value}")
                self.hardware.display.show_emotion(emotion, 1.0)
                time.sleep(0.5)

            # Test text display
            print("Testing text display...")
            test_texts = [
                "Hardware Test",
                "Display Working",
                "Mars Robot Ready"
            ]

            for text in test_texts:
                print(f"Displaying text: '{text}'")
                self.hardware.display.show_text(text)
                time.sleep(1)

            # Test status messages
            print("Testing status display...")
            status_levels = [
                ("info", "System operational"),
                ("warning", "Test in progress"),
                ("success", "All tests passing")
            ]

            for level, message in status_levels:
                print(f"Showing {level} status: '{message}'")
                self.hardware.display.show_status(message, level)
                time.sleep(1)

            # Test progress display
            print("Testing progress display...")
            for progress in [0.0, 0.25, 0.5, 0.75, 1.0]:
                self.hardware.display.show_progress(progress, f"Testing: {int(progress*100)}%")
                time.sleep(0.5)

            # Test different display modes
            print("Testing display modes...")
            modes = [
                ("idle", self.hardware.display.show_idle_mode),
                ("question", self.hardware.display.show_question_mode),
                ("follow", lambda: self.hardware.display.show_follow_mode("Patient"))
            ]

            for mode_name, mode_func in modes:
                print(f"Testing {mode_name} mode display")
                mode_func()
                time.sleep(1)

            # Test brightness control
            print("Testing brightness control...")
            original_brightness = self.hardware.display.get_brightness()

            for brightness in [0.3, 0.8, original_brightness]:
                self.hardware.display.set_brightness(brightness)
                current_brightness = self.hardware.display.get_brightness()
                print(f"Brightness set to {brightness:.1f}, current: {current_brightness:.1f}")

            # Test display resolution
            resolution = self.hardware.display.get_display_resolution()
            print(f"Display resolution: {resolution[0]}x{resolution[1]}")

            # Clear display
            self.hardware.display.clear_display()
            print("✓ Display cleared")

            return True

        except Exception as e:
            print(f"Display test error: {e}")
            return False

    def _test_emergency_stop(self) -> bool:
        """Test emergency stop functionality"""
        try:
            print("Testing emergency stop...")

            # Test hardware manager emergency stop
            print("Triggering hardware manager emergency stop...")
            self.hardware.emergency_stop()
            print("✓ Emergency stop executed")

            # Wait a moment
            time.sleep(1)

            # Test individual component emergency stops
            print("Testing individual component emergency stops...")

            components = [
                ("motors", self.hardware.motors.emergency_stop),
                ("arms", self.hardware.arms.emergency_stop),
                ("camera_servos", self.hardware.camera_servos.stop)
            ]

            for component_name, stop_func in components:
                print(f"Testing {component_name} emergency stop...")
                stop_func()
                print(f"✓ {component_name} emergency stop executed")

            return True

        except Exception as e:
            print(f"Emergency stop test error: {e}")
            return False

    def _print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("HARDWARE TEST SUMMARY")
        print("="*80)

        passed_tests = []
        failed_tests = []

        for test_name, result in self.test_results.items():
            if result:
                passed_tests.append(test_name)
            else:
                failed_tests.append(test_name)

        print(f"Total tests run: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")

        if passed_tests:
            print(f"\n✓ PASSED TESTS:")
            for test in passed_tests:
                print(f"  • {test}")

        if failed_tests:
            print(f"\n✗ FAILED TESTS:")
            for test in failed_tests:
                print(f"  • {test}")

        overall_result = len(failed_tests) == 0
        print(f"\nOVERALL RESULT: {'✓ ALL TESTS PASSED' if overall_result else '✗ SOME TESTS FAILED'}")

        # Save results to file
        self._save_test_results()

    def _save_test_results(self):
        """Save test results to file"""
        try:
            results_file = os.path.join(os.path.dirname(__file__), 'hardware_test_results.json')

            results_data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'hardware_mode': 'mock' if self.use_mock_hardware else 'real',
                'results': self.test_results,
                'summary': {
                    'total_tests': len(self.test_results),
                    'passed': sum(1 for r in self.test_results.values() if r),
                    'failed': sum(1 for r in self.test_results.values() if not r)
                }
            }

            with open(results_file, 'w') as f:
                json.dump(results_data, f, indent=2)

            print(f"\nTest results saved to: {results_file}")

        except Exception as e:
            print(f"Error saving test results: {e}")

    def cleanup(self):
        """Cleanup hardware resources"""
        try:
            print("\nCleaning up hardware...")
            self.hardware.shutdown()
            print("Hardware cleanup completed")
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Comprehensive hardware testing for Mars Robot')
    parser.add_argument('--mock', action='store_true',
                       help='Use mock hardware for testing')

    args = parser.parse_args()

    # Create tester
    tester = HardwareTester(use_mock_hardware=args.mock)

    try:
        # Run all tests
        success = tester.run_all_tests()

        if success:
            print("\n🎉 All hardware tests completed successfully!")
            sys.exit(0)
        else:
            print("\n⚠️  Some hardware tests failed. Check the results above.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nTesting interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during testing: {e}")
        sys.exit(1)
    finally:
        tester.cleanup()


if __name__ == '__main__':
    main()