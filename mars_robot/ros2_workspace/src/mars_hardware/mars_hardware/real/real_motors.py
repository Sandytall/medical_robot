"""
Real Motor Implementation for L298N on Raspberry Pi 5
"""
import time
from typing import Tuple, Dict, Any
from ..interfaces.motor_interface import MotorInterface

try:
    import lgpio
    GPIO_AVAILABLE = True
except ImportError:
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    except ImportError:
        GPIO_AVAILABLE = False


class RealMotors(MotorInterface):
    """Real L298N motor driver implementation for Raspberry Pi 5 using lgpio"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.gpio_handle = None
        self.is_initialized = False
        self.current_speeds = [0.0, 0.0]  # [left, right]
        self.max_speed = self.config.get('max_speed', 100.0)

        # L298N pin configuration from config
        motor_config = self.config.get('motors', {})
        self.left_motor = motor_config.get('left_motor', {})
        self.right_motor = motor_config.get('right_motor', {})

        # Pin assignments
        self.left_enable = self.left_motor.get('enable_pin', 18)
        self.left_in1 = self.left_motor.get('in1_pin', 19)
        self.left_in2 = self.left_motor.get('in2_pin', 20)

        self.right_enable = self.right_motor.get('enable_pin', 21)
        self.right_in1 = self.right_motor.get('in1_pin', 22)
        self.right_in2 = self.right_motor.get('in2_pin', 23)

        self.pwm_frequency = 1000  # 1kHz PWM frequency

    def initialize(self) -> bool:
        """Initialize L298N motor driver with lgpio"""
        if not GPIO_AVAILABLE:
            print("RealMotors: GPIO library not available (lgpio or RPi.GPIO)")
            return False

        try:
            # Open GPIO chip
            self.gpio_handle = lgpio.gpiochip_open(0)

            # Set GPIO modes for motor pins
            pins_to_setup = [
                self.left_enable, self.left_in1, self.left_in2,
                self.right_enable, self.right_in1, self.right_in2
            ]

            for pin in pins_to_setup:
                lgpio.gpio_claim_output(self.gpio_handle, pin, 0)

            # Initialize all pins to LOW
            for pin in pins_to_setup:
                lgpio.gpio_write(self.gpio_handle, pin, 0)

            self.is_initialized = True
            print("✅ RealMotors: L298N initialized successfully")
            return True

        except Exception as e:
            print(f"❌ RealMotors initialization failed: {e}")
            return False

    def _set_motor_direction_speed(self, motor: str, speed: float):
        """Set individual motor direction and speed"""
        if not self.is_initialized:
            return

        try:
            if motor == 'left':
                enable_pin = self.left_enable
                in1_pin = self.left_in1
                in2_pin = self.left_in2
            else:  # right
                enable_pin = self.right_enable
                in1_pin = self.right_in1
                in2_pin = self.right_in2

            # Clamp speed to limits
            speed = max(-self.max_speed, min(self.max_speed, speed))

            if speed > 0:
                # Forward direction
                lgpio.gpio_write(self.gpio_handle, in1_pin, 1)
                lgpio.gpio_write(self.gpio_handle, in2_pin, 0)
            elif speed < 0:
                # Reverse direction
                lgpio.gpio_write(self.gpio_handle, in1_pin, 0)
                lgpio.gpio_write(self.gpio_handle, in2_pin, 1)
                speed = abs(speed)
            else:
                # Stop
                lgpio.gpio_write(self.gpio_handle, in1_pin, 0)
                lgpio.gpio_write(self.gpio_handle, in2_pin, 0)

            # Set PWM duty cycle (0-255 for lgpio)
            duty_cycle = int((abs(speed) / self.max_speed) * 255)
            lgpio.tx_pwm(self.gpio_handle, enable_pin, self.pwm_frequency, duty_cycle)

        except Exception as e:
            print(f"❌ Motor {motor} control error: {e}")

    def set_motor_speed(self, left_speed: float, right_speed: float):
        """Set both motor speeds (-100 to +100)"""
        self.current_speeds = [left_speed, right_speed]
        self._set_motor_direction_speed('left', left_speed)
        self._set_motor_direction_speed('right', right_speed)

    def move_forward(self, speed: float = 50.0):
        """Move forward at specified speed"""
        self.set_motor_speed(speed, speed)

    def move_backward(self, speed: float = 50.0):
        """Move backward at specified speed"""
        self.set_motor_speed(-speed, -speed)

    def turn_left(self, speed: float = 50.0):
        """Turn left by rotating motors in opposite directions"""
        self.set_motor_speed(-speed, speed)

    def turn_right(self, speed: float = 50.0):
        """Turn right by rotating motors in opposite directions"""
        self.set_motor_speed(speed, -speed)

    def stop(self):
        """Stop both motors"""
        self.set_motor_speed(0.0, 0.0)

    def emergency_stop(self):
        """Emergency stop - immediately stop all motors"""
        self.stop()
        print("🚨 RealMotors: Emergency stop activated")

    def get_motor_speeds(self) -> Tuple[float, float]:
        """Get current motor speeds"""
        return tuple(self.current_speeds)

    def set_speed_limit(self, max_speed: float):
        """Set maximum speed limit"""
        self.max_speed = max(0.0, min(100.0, max_speed))

    def get_speed_limit(self) -> float:
        """Get current speed limit"""
        return self.max_speed

    def is_connected(self) -> bool:
        """Check if motors are connected and initialized"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get motor status information"""
        return {
            'initialized': self.is_initialized,
            'current_speeds': self.current_speeds,
            'max_speed': self.max_speed,
            'gpio_available': GPIO_AVAILABLE,
            'pins': {
                'left_motor': {
                    'enable': self.left_enable,
                    'in1': self.left_in1,
                    'in2': self.left_in2
                },
                'right_motor': {
                    'enable': self.right_enable,
                    'in1': self.right_in1,
                    'in2': self.right_in2
                }
            }
        }

    def shutdown(self):
        """Properly shutdown motors and cleanup GPIO"""
        try:
            # Stop motors first
            self.stop()
            time.sleep(0.1)  # Brief delay to ensure motors stop

            # Cleanup GPIO
            if self.gpio_handle is not None:
                # Turn off PWM
                pins_to_cleanup = [
                    self.left_enable, self.left_in1, self.left_in2,
                    self.right_enable, self.right_in1, self.right_in2
                ]

                for pin in pins_to_cleanup:
                    try:
                        lgpio.gpio_write(self.gpio_handle, pin, 0)
                        lgpio.gpio_free(self.gpio_handle, pin)
                    except:
                        pass  # Ignore cleanup errors

                lgpio.gpiochip_close(self.gpio_handle)
                self.gpio_handle = None

            self.is_initialized = False
            print("✅ RealMotors: Shutdown completed")

        except Exception as e:
            print(f"⚠️  RealMotors shutdown error: {e}")