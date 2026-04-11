"""Real Camera Servos Implementation for Pan/Tilt on Raspberry Pi 5"""
import time
import threading
from typing import Tuple, Dict, Any
from ..interfaces.camera_servo_interface import CameraServoInterface

try:
    import lgpio
    GPIO_AVAILABLE = True
except ImportError:
    try:
        import RPi.GPIO as GPIO
        GPIO_AVAILABLE = True
    except ImportError:
        GPIO_AVAILABLE = False


class RealCameraServos(CameraServoInterface):
    """Real camera pan/tilt servo implementation for Raspberry Pi 5 using lgpio"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.gpio_handle = None
        self.is_initialized = False
        self.movement_lock = threading.Lock()
        self.is_moving_flag = False

        # Servo configuration from config
        pan_config = self.config.get('pan_servo', {})
        tilt_config = self.config.get('tilt_servo', {})

        # GPIO pin assignments
        self.pan_pin = pan_config.get('pin', 10)
        self.tilt_pin = tilt_config.get('pin', 11)

        # Servo angle limits
        self.pan_range = pan_config.get('range', [-90, 90])
        self.tilt_range = tilt_config.get('range', [-45, 45])

        # Current positions
        self.pan_angle = pan_config.get('center_angle', 0.0)
        self.tilt_angle = tilt_config.get('center_angle', 0.0)

        # Movement settings
        self.movement_speed = self.config.get('movement_speed', 0.5)
        self.servo_frequency = 50  # 50Hz for servos
        self.pulse_min = 500       # 0.5ms = 0 degrees
        self.pulse_max = 2500      # 2.5ms = 180 degrees

        print(f"RealCameraServos: Pan pin {self.pan_pin}, Tilt pin {self.tilt_pin}")

    def initialize(self) -> bool:
        """Initialize camera servo hardware using lgpio"""
        if not GPIO_AVAILABLE:
            print("❌ RealCameraServos: GPIO library not available (lgpio or RPi.GPIO)")
            return False

        try:
            # Open GPIO chip
            self.gpio_handle = lgpio.gpiochip_open(0)

            # Setup GPIO pins for servos
            lgpio.gpio_claim_output(self.gpio_handle, self.pan_pin, 0)
            lgpio.gpio_claim_output(self.gpio_handle, self.tilt_pin, 0)

            # Move to center position
            self.center_camera()

            self.is_initialized = True
            print(f"✅ RealCameraServos: Camera pan/tilt servos initialized")
            return True

        except Exception as e:
            print(f"❌ RealCameraServos initialization failed: {e}")
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
            print(f"❌ Camera servo PWM error on pin {pin}: {e}")

    def set_pan_angle(self, angle: float):
        """Set pan servo angle"""
        if not self.is_initialized:
            return

        # Validate angle against limits
        angle = max(self.pan_range[0], min(self.pan_range[1], angle))

        with self.movement_lock:
            self._set_servo_pwm(self.pan_pin, angle)
            self.pan_angle = angle

    def set_tilt_angle(self, angle: float):
        """Set tilt servo angle"""
        if not self.is_initialized:
            return

        # Validate angle against limits
        angle = max(self.tilt_range[0], min(self.tilt_range[1], angle))

        with self.movement_lock:
            self._set_servo_pwm(self.tilt_pin, angle)
            self.tilt_angle = angle

    def get_pan_angle(self) -> float:
        """Get current pan angle"""
        return self.pan_angle

    def get_tilt_angle(self) -> float:
        """Get current tilt angle"""
        return self.tilt_angle

    def set_pan_tilt(self, pan: float, tilt: float):
        """Set both pan and tilt angles simultaneously"""
        if not self.is_initialized:
            return

        # Validate angles against limits
        pan = max(self.pan_range[0], min(self.pan_range[1], pan))
        tilt = max(self.tilt_range[0], min(self.tilt_range[1], tilt))

        with self.movement_lock:
            self.is_moving_flag = True
            try:
                # Smooth movement to target position
                start_pan, start_tilt = self.pan_angle, self.tilt_angle
                steps = max(10, int(20 * self.movement_speed))

                for step in range(steps + 1):
                    progress = step / steps
                    current_pan = start_pan + (pan - start_pan) * progress
                    current_tilt = start_tilt + (tilt - start_tilt) * progress

                    self._set_servo_pwm(self.pan_pin, current_pan)
                    self._set_servo_pwm(self.tilt_pin, current_tilt)

                    time.sleep(0.02)  # 20ms between steps

                self.pan_angle = pan
                self.tilt_angle = tilt

            except Exception as e:
                print(f"❌ Camera servo set_pan_tilt error: {e}")
            finally:
                self.is_moving_flag = False

    def get_pan_tilt(self) -> Tuple[float, float]:
        """Get current pan and tilt angles"""
        return (self.pan_angle, self.tilt_angle)

    def center_camera(self):
        """Move camera to center position (0, 0)"""
        self.set_pan_tilt(0.0, 0.0)

    def look_left(self, angle: float = 45.0):
        """Look left by specified angle"""
        target_angle = max(self.pan_range[0], min(self.pan_range[1], angle))
        self.set_pan_angle(target_angle)

    def look_right(self, angle: float = 45.0):
        """Look right by specified angle"""
        target_angle = max(self.pan_range[0], min(self.pan_range[1], -angle))
        self.set_pan_angle(target_angle)

    def look_up(self, angle: float = 30.0):
        """Look up by specified angle"""
        target_angle = max(self.tilt_range[0], min(self.tilt_range[1], angle))
        self.set_tilt_angle(target_angle)

    def look_down(self, angle: float = 30.0):
        """Look down by specified angle"""
        target_angle = max(self.tilt_range[0], min(self.tilt_range[1], -angle))
        self.set_tilt_angle(target_angle)

    def scan_area(self, scan_pattern: str = "horizontal"):
        """Scan area in specified pattern"""
        if not self.is_initialized:
            return

        def _scan_thread():
            try:
                if scan_pattern == "horizontal":
                    # Horizontal scan: center -> left -> right -> center
                    positions = [(0, 0), (60, 0), (-60, 0), (0, 0)]
                elif scan_pattern == "vertical":
                    # Vertical scan: center -> up -> down -> center
                    positions = [(0, 0), (0, 30), (0, -30), (0, 0)]
                elif scan_pattern == "cross":
                    # Cross pattern scan
                    positions = [(0, 0), (45, 0), (-45, 0), (0, 0), (0, 30), (0, -30), (0, 0)]
                else:
                    # Default circular scan
                    positions = [(0, 0), (45, 20), (0, 30), (-45, 20), (-45, -20), (0, -30), (45, -20), (0, 0)]

                for pan, tilt in positions:
                    self.set_pan_tilt(pan, tilt)
                    time.sleep(1.0 / self.movement_speed)

            except Exception as e:
                print(f"❌ Camera scan error: {e}")

        # Run scan in background thread
        threading.Thread(target=_scan_thread, daemon=True).start()

    def follow_target(self, target_x: float, target_y: float, image_width: int, image_height: int):
        """Calculate pan/tilt to follow target in camera frame"""
        if not self.is_initialized:
            return

        try:
            # Calculate normalized coordinates (-1 to 1)
            norm_x = (target_x - image_width / 2) / (image_width / 2)
            norm_y = (target_y - image_height / 2) / (image_height / 2)

            # Calculate pan/tilt adjustments
            max_pan_range = abs(self.pan_range[1] - self.pan_range[0]) / 2
            max_tilt_range = abs(self.tilt_range[1] - self.tilt_range[0]) / 2

            pan_adjustment = norm_x * max_pan_range * 0.3  # Scale factor for responsiveness
            tilt_adjustment = -norm_y * max_tilt_range * 0.3  # Inverted Y for intuitive control

            # Apply adjustments to current position
            new_pan = self.pan_angle + pan_adjustment
            new_tilt = self.tilt_angle + tilt_adjustment

            # Only move if adjustment is significant
            if abs(pan_adjustment) > 2.0 or abs(tilt_adjustment) > 2.0:
                self.set_pan_tilt(new_pan, new_tilt)

        except Exception as e:
            print(f"❌ Camera follow_target error: {e}")

    def set_movement_speed(self, speed: float):
        """Set movement speed (0.1 to 2.0)"""
        self.movement_speed = max(0.1, min(2.0, speed))

    def get_movement_speed(self) -> float:
        """Get current movement speed"""
        return self.movement_speed

    def is_moving(self) -> bool:
        """Check if servos are currently moving"""
        return self.is_moving_flag

    def stop(self):
        """Stop servo movement (servos hold current position)"""
        # Servos naturally hold position when PWM is maintained
        pass

    def get_limits(self) -> Dict[str, Tuple[float, float]]:
        """Get servo angle limits"""
        return {
            'pan': tuple(self.pan_range),
            'tilt': tuple(self.tilt_range)
        }

    def is_connected(self) -> bool:
        """Check if camera servos are connected and initialized"""
        return self.is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get camera servo status information"""
        return {
            'initialized': self.is_initialized,
            'pan_angle': self.pan_angle,
            'tilt_angle': self.tilt_angle,
            'moving': self.is_moving_flag,
            'movement_speed': self.movement_speed,
            'gpio_available': GPIO_AVAILABLE,
            'pins': {
                'pan_pin': self.pan_pin,
                'tilt_pin': self.tilt_pin
            },
            'limits': {
                'pan_range': self.pan_range,
                'tilt_range': self.tilt_range
            }
        }

    def shutdown(self):
        """Properly shutdown camera servos and cleanup GPIO"""
        try:
            # Wait for any movement to complete
            while self.is_moving_flag:
                time.sleep(0.1)

            # Move to center position before shutdown
            if self.is_initialized:
                self.center_camera()
                time.sleep(1.0)

            # Cleanup GPIO
            if self.gpio_handle is not None:
                try:
                    # Stop PWM and free pins
                    lgpio.tx_pwm(self.gpio_handle, self.pan_pin, 0, 0)
                    lgpio.tx_pwm(self.gpio_handle, self.tilt_pin, 0, 0)
                    lgpio.gpio_free(self.gpio_handle, self.pan_pin)
                    lgpio.gpio_free(self.gpio_handle, self.tilt_pin)
                except:
                    pass  # Ignore cleanup errors

                lgpio.gpiochip_close(self.gpio_handle)
                self.gpio_handle = None

            self.is_initialized = False
            print("✅ RealCameraServos: Shutdown completed")

        except Exception as e:
            print(f"⚠️  RealCameraServos shutdown error: {e}")