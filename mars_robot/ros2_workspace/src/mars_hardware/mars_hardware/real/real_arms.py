"""Real Arms Implementation for Servo Motors on Raspberry Pi 5"""
import time
import threading
from typing import List, Dict, Any, Tuple
from ..interfaces.arm_interface import ArmInterface, ArmSide

try:
    import lgpio
    GPIO_AVAILABLE = True
except ImportError:
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
        USE_RPI_GPIO = True
    except ImportError:
        GPIO_AVAILABLE = False
        USE_RPI_GPIO = False


class RealArms(ArmInterface):
    """Real servo motor implementation for robotic arms on Raspberry Pi 5 using lgpio"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.gpio_handle = None
        self.is_initialized = False
        self.current_positions = {ArmSide.LEFT: [0.0, 0.0, 0.0, 0.0], ArmSide.RIGHT: [0.0, 0.0, 0.0, 0.0]}
        self.movement_speed = 0.5
        self.is_moving_flag = {ArmSide.LEFT: False, ArmSide.RIGHT: False}
        self.movement_lock = threading.Lock()

        # Servo configuration from config
        arms_config = self.config.get('arms', {})
        self.left_arm = arms_config.get('left_arm', {})
        self.right_arm = arms_config.get('right_arm', {})

        # Servo pin assignments
        self.servo_pins = {
            ArmSide.LEFT: self.left_arm.get('servos', [2, 3, 4, 5]),
            ArmSide.RIGHT: self.right_arm.get('servos', [6, 7, 8, 9])
        }

        # Servo angle limits
        self.servo_limits = {
            ArmSide.LEFT: self.left_arm.get('servo_limits', [[-90, 90]] * 4),
            ArmSide.RIGHT: self.right_arm.get('servo_limits', [[-90, 90]] * 4)
        }

        # Servo PWM settings
        self.servo_frequency = 50  # 50Hz for servos
        self.pulse_min = 500       # 0.5ms = 0 degrees
        self.pulse_max = 2500      # 2.5ms = 180 degrees

        # Preset positions
        self.presets = arms_config.get('presets', {
            'home': {ArmSide.LEFT: [0, 0, 0, 0], ArmSide.RIGHT: [0, 0, 0, 0]},
            'wave': {ArmSide.LEFT: [0, 45, -45, 0], ArmSide.RIGHT: [0, 45, -45, 0]},
            'greet': {ArmSide.LEFT: [-30, 60, -30, 0], ArmSide.RIGHT: [30, 60, -30, 0]}
        })

    def initialize(self) -> bool:
        """Initialize servo motors using lgpio"""
        if not GPIO_AVAILABLE:
            print("❌ RealArms: GPIO library not available (lgpio or RPi.GPIO)")
            return False

        try:
            # Open GPIO chip
            self.gpio_handle = lgpio.gpiochip_open(0)

            # Initialize all servo pins
            all_servo_pins = self.servo_pins[ArmSide.LEFT] + self.servo_pins[ArmSide.RIGHT]
            for pin in all_servo_pins:
                lgpio.gpio_claim_output(self.gpio_handle, pin, 0)

            # Move to home position
            self.move_to_home_position()

            self.is_initialized = True
            print(f"✅ RealArms: {len(all_servo_pins)} servo motors initialized")
            return True

        except Exception as e:
            print(f"❌ RealArms initialization failed: {e}")
            return False

    def _angle_to_pulse_width(self, angle: float) -> int:
        """Convert angle (-90 to +90) to pulse width in microseconds"""
        # Normalize angle to 0-180 range
        normalized_angle = angle + 90
        normalized_angle = max(0, min(180, normalized_angle))

        # Calculate pulse width
        pulse_width = self.pulse_min + (normalized_angle / 180.0) * (self.pulse_max - self.pulse_min)
        return int(pulse_width)

    def _set_servo_pwm(self, pin: int, angle: float):
        """Set PWM for individual servo"""
        if not self.is_initialized:
            return

        try:
            pulse_width = self._angle_to_pulse_width(angle)
            # Convert to duty cycle for lgpio (0-255)
            duty_cycle = int((pulse_width / 20000.0) * 255)  # 20ms period
            lgpio.tx_pwm(self.gpio_handle, pin, self.servo_frequency, duty_cycle)
        except Exception as e:
            print(f"❌ Servo PWM error on pin {pin}: {e}")

    def set_servo_angle(self, arm: ArmSide, joint: int, angle: float):
        """Set individual servo angle"""
        if not self.is_initialized or not (0 <= joint < 4):
            return

        try:
            # Validate angle against limits
            limits = self.servo_limits[arm][joint]
            angle = max(limits[0], min(limits[1], angle))

            # Set servo angle
            pin = self.servo_pins[arm][joint]
            self._set_servo_pwm(pin, angle)

            # Update current position
            self.current_positions[arm][joint] = angle

        except Exception as e:
            print(f"❌ RealArms set_servo_angle error: {e}")

    def get_servo_angle(self, arm: ArmSide, joint: int) -> float:
        """Get current servo angle"""
        if arm in self.current_positions and 0 <= joint < 4:
            return self.current_positions[arm][joint]
        return 0.0

    def set_arm_angles(self, arm: ArmSide, angles: List[float]):
        """Set all servo angles for an arm"""
        if not self.is_initialized or len(angles) != 4:
            return

        try:
            self.is_moving_flag[arm] = True

            # Set all servos with smooth movement
            pins = self.servo_pins[arm]
            limits = self.servo_limits[arm]
            current = self.current_positions[arm]

            # Validate angles
            validated_angles = []
            for i, (angle, limit) in enumerate(zip(angles, limits)):
                validated_angles.append(max(limit[0], min(limit[1], angle)))

            # Smooth movement
            steps = 20
            for step in range(steps + 1):
                progress = step / steps
                for i in range(4):
                    interpolated = current[i] + (validated_angles[i] - current[i]) * progress
                    self._set_servo_pwm(pins[i], interpolated)
                    self.current_positions[arm][i] = interpolated

                time.sleep(self.movement_speed / steps)

        except Exception as e:
            print(f"❌ RealArms set_arm_angles error: {e}")
        finally:
            self.is_moving_flag[arm] = False

    def get_arm_angles(self, arm: ArmSide) -> List[float]:
        """Get current arm angles"""
        return self.current_positions[arm][:]

    def move_to_home_position(self, arm: ArmSide = None):
        """Move arm(s) to home position"""
        home_position = [0.0, 0.0, 0.0, 0.0]

        if arm is None:
            # Move both arms
            threading.Thread(target=self.set_arm_angles, args=(ArmSide.LEFT, home_position), daemon=True).start()
            threading.Thread(target=self.set_arm_angles, args=(ArmSide.RIGHT, home_position), daemon=True).start()
        else:
            # Move specific arm
            threading.Thread(target=self.set_arm_angles, args=(arm, home_position), daemon=True).start()

    def move_to_preset_position(self, arm: ArmSide, preset_name: str) -> bool:
        """Move arm to preset position"""
        if preset_name not in self.presets:
            print(f"❌ RealArms: Unknown preset '{preset_name}'")
            return False

        try:
            preset_angles = self.presets[preset_name][arm]
            threading.Thread(target=self.set_arm_angles, args=(arm, preset_angles), daemon=True).start()
            return True
        except Exception as e:
            print(f"❌ RealArms move_to_preset_position error: {e}")
            return False

    def add_preset_position(self, preset_name: str, left_angles: List[float], right_angles: List[float]):
        """Add new preset position"""
        self.presets[preset_name] = {
            ArmSide.LEFT: left_angles[:],
            ArmSide.RIGHT: right_angles[:]
        }

    def get_preset_positions(self) -> List[str]:
        """Get list of available presets"""
        return list(self.presets.keys())

    def set_movement_speed(self, speed: float):
        """Set movement speed (0.1 to 2.0)"""
        self.movement_speed = max(0.1, min(2.0, speed))

    def get_movement_speed(self) -> float:
        """Get current movement speed"""
        return self.movement_speed

    def is_moving(self, arm: ArmSide = None) -> bool:
        """Check if arm(s) are currently moving"""
        if arm is None:
            return any(self.is_moving_flag.values())
        return self.is_moving_flag.get(arm, False)

    def emergency_stop(self):
        """Emergency stop - hold current positions"""
        print("🚨 RealArms: Emergency stop activated")
        # Servos will hold current position automatically

    def get_servo_limits(self, arm: ArmSide, joint: int) -> Tuple[float, float]:
        """Get servo angle limits"""
        if arm in self.servo_limits and 0 <= joint < 4:
            return tuple(self.servo_limits[arm][joint])
        return (-90.0, 90.0)

    def is_connected(self) -> bool:
        """Check if arms are connected and initialized"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get arms status information"""
        return {
            'initialized': self.is_initialized,
            'moving': {arm.value: self.is_moving_flag[arm] for arm in ArmSide},
            'positions': {arm.value: self.current_positions[arm] for arm in ArmSide},
            'movement_speed': self.movement_speed,
            'gpio_available': GPIO_AVAILABLE,
            'servo_pins': {arm.value: self.servo_pins[arm] for arm in ArmSide},
            'presets': list(self.presets.keys())
        }

    def shutdown(self):
        """Properly shutdown servo motors and cleanup GPIO"""
        try:
            # Wait for any ongoing movement to complete
            while any(self.is_moving_flag.values()):
                time.sleep(0.1)

            # Move to safe home position
            if self.is_initialized:
                self.move_to_home_position()
                time.sleep(2.0)  # Wait for movement to complete

            # Cleanup GPIO
            if self.gpio_handle is not None:
                all_servo_pins = self.servo_pins[ArmSide.LEFT] + self.servo_pins[ArmSide.RIGHT]
                for pin in all_servo_pins:
                    try:
                        # Stop PWM and free pin
                        lgpio.tx_pwm(self.gpio_handle, pin, 0, 0)
                        lgpio.gpio_free(self.gpio_handle, pin)
                    except:
                        pass  # Ignore cleanup errors

                lgpio.gpiochip_close(self.gpio_handle)
                self.gpio_handle = None

            self.is_initialized = False
            print("✅ RealArms: Shutdown completed")

        except Exception as e:
            print(f"⚠️  RealArms shutdown error: {e}")