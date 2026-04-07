#!/usr/bin/env python3
"""
Gamepad Testing Script for Mars Robot
Tests gamepad buttons and joystick inputs for manual control mode
"""
import os
import sys
import time
import argparse
from typing import Dict, Any, List

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Pygame not available. Install with: pip install pygame")

try:
    import inputs
    INPUTS_AVAILABLE = True
except ImportError:
    INPUTS_AVAILABLE = False
    print("inputs library not available. Install with: pip install inputs")


class GamepadTester:
    """Gamepad testing utility"""

    def __init__(self, use_pygame: bool = True):
        self.use_pygame = use_pygame and PYGAME_AVAILABLE
        self.running = False

        # Gamepad state
        self.joystick = None
        self.button_states = {}
        self.axis_values = {}
        self.last_input_time = time.time()

        # Input mapping for common gamepads
        self.button_mapping = {
            0: 'A / X',           # Cross/A button
            1: 'B / Circle',      # Circle/B button
            2: 'X / Square',      # Square/X button
            3: 'Y / Triangle',    # Triangle/Y button
            4: 'LB / L1',         # Left bumper
            5: 'RB / R1',         # Right bumper
            6: 'Back / Select',   # Back/Select button
            7: 'Start',           # Start button
            8: 'Left Stick',      # Left stick button
            9: 'Right Stick',     # Right stick button
            10: 'Xbox / PS'       # Xbox/PlayStation button
        }

        self.axis_mapping = {
            0: 'Left Stick X',    # Left stick horizontal
            1: 'Left Stick Y',    # Left stick vertical
            2: 'Left Trigger',    # Left trigger (Xbox)
            3: 'Right Stick X',   # Right stick horizontal
            4: 'Right Stick Y',   # Right stick vertical
            5: 'Right Trigger'    # Right trigger (Xbox)
        }

        # Movement configuration
        self.speed_levels = {
            'slow': 0.3,
            'normal': 0.6,
            'fast': 1.0
        }
        self.current_speed_level = 'normal'

        print(f"Gamepad Tester initialized (using {'pygame' if self.use_pygame else 'inputs'})")

    def initialize(self) -> bool:
        """Initialize gamepad interface"""
        try:
            if self.use_pygame:
                return self._initialize_pygame()
            else:
                return self._initialize_inputs()
        except Exception as e:
            print(f"Failed to initialize gamepad: {e}")
            return False

    def _initialize_pygame(self) -> bool:
        """Initialize pygame gamepad interface"""
        try:
            pygame.init()
            pygame.joystick.init()

            # Check for connected joysticks
            joystick_count = pygame.joystick.get_count()
            print(f"Found {joystick_count} gamepad(s)")

            if joystick_count == 0:
                print("No gamepads detected. Please connect a gamepad and restart.")
                return False

            # Use first gamepad
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

            print(f"Gamepad connected: {self.joystick.get_name()}")
            print(f"Axes: {self.joystick.get_numaxes()}")
            print(f"Buttons: {self.joystick.get_numbuttons()}")
            print(f"Hats: {self.joystick.get_numhats()}")

            return True

        except Exception as e:
            print(f"Pygame initialization failed: {e}")
            return False

    def _initialize_inputs(self) -> bool:
        """Initialize inputs library interface"""
        try:
            # Check for available gamepads
            devices = inputs.DeviceManager()
            gamepads = devices.gamepads

            if not gamepads:
                print("No gamepads detected with inputs library")
                return False

            print(f"Found {len(gamepads)} gamepad(s) with inputs library:")
            for i, gamepad in enumerate(gamepads):
                print(f"  {i}: {gamepad}")

            return True

        except Exception as e:
            print(f"Inputs library initialization failed: {e}")
            return False

    def test_gamepad(self):
        """Main gamepad testing loop"""
        print("\n" + "="*60)
        print("GAMEPAD TESTING MODE")
        print("="*60)
        print("Testing gamepad inputs for Mars Robot manual control")
        print("Press CTRL+C to exit")
        print("\nControl Scheme:")
        print("  Left Stick: Forward/Backward movement")
        print("  Right Stick: Left/Right turning")
        print("  L1/LB: Decrease speed level")
        print("  R1/RB: Increase speed level")
        print("  X/A: Emergency stop")
        print("  Start: Exit test")
        print("-"*60)

        self.running = True

        try:
            if self.use_pygame:
                self._test_with_pygame()
            else:
                self._test_with_inputs()

        except KeyboardInterrupt:
            print("\nTesting stopped by user")
        except Exception as e:
            print(f"Error during testing: {e}")
        finally:
            self.cleanup()

    def _test_with_pygame(self):
        """Test gamepad using pygame"""
        clock = pygame.time.Clock()

        while self.running:
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.JOYBUTTONDOWN:
                    self._handle_button_press(event.button, True)

                elif event.type == pygame.JOYBUTTONUP:
                    self._handle_button_press(event.button, False)

                elif event.type == pygame.JOYAXISMOTION:
                    self._handle_axis_motion(event.axis, event.value)

                elif event.type == pygame.JOYHATMOTION:
                    self._handle_hat_motion(event.hat, event.value)

            # Update display every 100ms
            if time.time() - self.last_input_time > 0.1:
                self._display_status()
                self.last_input_time = time.time()

            clock.tick(60)  # 60 FPS

    def _test_with_inputs(self):
        """Test gamepad using inputs library"""
        print("Listening for gamepad inputs (inputs library)...")

        while self.running:
            try:
                events = inputs.get_gamepad()
                for event in events:
                    if event.ev_type == 'Key':
                        # Button event
                        button_code = event.code
                        pressed = event.state == 1
                        self._handle_button_event(button_code, pressed)

                    elif event.ev_type == 'Absolute':
                        # Axis event
                        axis_code = event.code
                        value = event.state
                        self._handle_axis_event(axis_code, value)

            except inputs.UnpluggedError:
                print("Gamepad unplugged!")
                break
            except Exception as e:
                print(f"Input error: {e}")
                time.sleep(0.1)

    def _handle_button_press(self, button: int, pressed: bool):
        """Handle button press/release"""
        self.button_states[button] = pressed

        button_name = self.button_mapping.get(button, f"Button {button}")
        state = "PRESSED" if pressed else "RELEASED"

        print(f"[BUTTON] {button_name}: {state}")

        if pressed:
            # Handle special button actions
            if button == 0:  # A/X button - Emergency stop
                print(">>> EMERGENCY STOP ACTIVATED <<<")
                self._emergency_stop()

            elif button == 4:  # LB/L1 - Decrease speed
                self._change_speed_level(-1)

            elif button == 5:  # RB/R1 - Increase speed
                self._change_speed_level(1)

            elif button == 7:  # Start - Exit
                print("Start button pressed - exiting test")
                self.running = False

    def _handle_axis_motion(self, axis: int, value: float):
        """Handle joystick axis motion"""
        # Apply deadzone
        deadzone = 0.1
        if abs(value) < deadzone:
            value = 0.0

        self.axis_values[axis] = value

        axis_name = self.axis_mapping.get(axis, f"Axis {axis}")

        # Only print significant changes
        if abs(value) > 0.1:
            print(f"[AXIS] {axis_name}: {value:.3f}")

        # Calculate robot movement
        self._calculate_robot_movement()

    def _handle_hat_motion(self, hat: int, value: tuple):
        """Handle D-pad motion"""
        print(f"[D-PAD] Hat {hat}: {value}")

    def _handle_button_event(self, code: str, pressed: bool):
        """Handle button event from inputs library"""
        print(f"[BUTTON] {code}: {'PRESSED' if pressed else 'RELEASED'}")

    def _handle_axis_event(self, code: str, value: int):
        """Handle axis event from inputs library"""
        # Normalize axis values (inputs library uses different ranges)
        if 'ABS_' in code:
            normalized_value = (value - 32768) / 32768.0  # Convert to -1.0 to 1.0
            if abs(normalized_value) > 0.1:  # Apply deadzone
                print(f"[AXIS] {code}: {normalized_value:.3f}")

    def _calculate_robot_movement(self):
        """Calculate robot movement based on joystick inputs"""
        try:
            # Get axis values (using pygame mapping)
            left_stick_y = -self.axis_values.get(1, 0.0)  # Forward/backward (inverted)
            right_stick_x = self.axis_values.get(3, 0.0)  # Left/right turning

            # Calculate motor speeds
            current_speed = self.speed_levels[self.current_speed_level]

            # Differential drive calculation
            linear_velocity = left_stick_y * current_speed
            angular_velocity = right_stick_x * current_speed

            # Calculate left and right motor speeds
            left_motor = linear_velocity - angular_velocity
            right_motor = linear_velocity + angular_velocity

            # Clamp to [-1.0, 1.0]
            left_motor = max(-1.0, min(1.0, left_motor))
            right_motor = max(-1.0, min(1.0, right_motor))

            # Only print if there's significant movement
            if abs(left_motor) > 0.1 or abs(right_motor) > 0.1:
                print(f"[MOVEMENT] Left: {left_motor:.2f}, Right: {right_motor:.2f} ({self.current_speed_level})")

        except Exception as e:
            print(f"Error calculating movement: {e}")

    def _change_speed_level(self, direction: int):
        """Change speed level"""
        speed_levels = list(self.speed_levels.keys())
        current_index = speed_levels.index(self.current_speed_level)

        new_index = current_index + direction
        if 0 <= new_index < len(speed_levels):
            self.current_speed_level = speed_levels[new_index]
            speed_value = self.speed_levels[self.current_speed_level]
            print(f"[SPEED] Changed to {self.current_speed_level} ({speed_value:.1f})")

    def _emergency_stop(self):
        """Execute emergency stop"""
        print(">>> EMERGENCY STOP: All movement halted <<<")
        # In real implementation, this would immediately stop all motors

    def _display_status(self):
        """Display current status"""
        # Clear previous lines and show current state
        if self.axis_values:
            status_line = f"Speed: {self.current_speed_level} | "

            # Show active axes
            active_axes = [(axis, value) for axis, value in self.axis_values.items() if abs(value) > 0.1]
            if active_axes:
                axis_info = ", ".join([f"{self.axis_mapping.get(axis, f'Axis{axis}')}:{value:.2f}"
                                     for axis, value in active_axes])
                status_line += axis_info
            else:
                status_line += "No movement"

            # Show active buttons
            active_buttons = [button for button, pressed in self.button_states.items() if pressed]
            if active_buttons:
                button_info = ", ".join([self.button_mapping.get(btn, f'Btn{btn}') for btn in active_buttons])
                status_line += f" | Buttons: {button_info}"

            # Only print if different from last status
            if hasattr(self, '_last_status') and status_line == self._last_status:
                return

            self._last_status = status_line
            print(f"[STATUS] {status_line}")

    def test_individual_inputs(self):
        """Test individual gamepad inputs"""
        print("\n" + "="*60)
        print("INDIVIDUAL INPUT TESTING")
        print("="*60)
        print("Press each button and move each axis to test")
        print("This will help identify button/axis mappings")
        print("Press CTRL+C to exit")
        print("-"*60)

        if not self.use_pygame:
            print("Individual testing only available with pygame")
            return

        self.running = True
        clock = pygame.time.Clock()

        try:
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False

                    elif event.type == pygame.JOYBUTTONDOWN:
                        print(f"Button {event.button} PRESSED ({self.button_mapping.get(event.button, 'Unknown')})")

                    elif event.type == pygame.JOYBUTTONUP:
                        print(f"Button {event.button} RELEASED ({self.button_mapping.get(event.button, 'Unknown')})")

                    elif event.type == pygame.JOYAXISMOTION:
                        if abs(event.value) > 0.1:  # Only show significant movements
                            axis_name = self.axis_mapping.get(event.axis, f'Unknown Axis {event.axis}')
                            print(f"Axis {event.axis} ({axis_name}): {event.value:.3f}")

                    elif event.type == pygame.JOYHATMOTION:
                        print(f"D-Pad {event.hat}: {event.value}")

                clock.tick(60)

        except KeyboardInterrupt:
            print("\nIndividual testing stopped")
        finally:
            self.cleanup()

    def get_gamepad_info(self):
        """Get detailed gamepad information"""
        if not self.use_pygame or not self.joystick:
            print("Gamepad info only available with pygame")
            return

        print("\n" + "="*60)
        print("GAMEPAD INFORMATION")
        print("="*60)
        print(f"Name: {self.joystick.get_name()}")
        print(f"ID: {self.joystick.get_id()}")
        print(f"GUID: {self.joystick.get_guid()}")
        print(f"Number of axes: {self.joystick.get_numaxes()}")
        print(f"Number of buttons: {self.joystick.get_numbuttons()}")
        print(f"Number of hats: {self.joystick.get_numhats()}")
        print("-"*60)

    def cleanup(self):
        """Cleanup gamepad resources"""
        self.running = False
        if self.use_pygame:
            if self.joystick:
                self.joystick.quit()
            pygame.quit()
        print("Gamepad testing cleanup completed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test gamepad for Mars Robot')
    parser.add_argument('--mode', choices=['test', 'individual', 'info'], default='test',
                       help='Testing mode (default: test)')
    parser.add_argument('--backend', choices=['pygame', 'inputs'], default='pygame',
                       help='Input backend to use (default: pygame)')

    args = parser.parse_args()

    # Check if required libraries are available
    if args.backend == 'pygame' and not PYGAME_AVAILABLE:
        print("Pygame not available. Install with: pip install pygame")
        sys.exit(1)
    elif args.backend == 'inputs' and not INPUTS_AVAILABLE:
        print("inputs library not available. Install with: pip install inputs")
        sys.exit(1)

    # Create tester
    tester = GamepadTester(use_pygame=(args.backend == 'pygame'))

    # Initialize
    if not tester.initialize():
        print("Failed to initialize gamepad")
        sys.exit(1)

    # Run selected mode
    try:
        if args.mode == 'test':
            tester.test_gamepad()
        elif args.mode == 'individual':
            tester.test_individual_inputs()
        elif args.mode == 'info':
            tester.get_gamepad_info()

    except Exception as e:
        print(f"Error during gamepad testing: {e}")
    finally:
        tester.cleanup()


if __name__ == '__main__':
    main()