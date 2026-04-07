"""
Mars Robot Hardware Manager
Detects environment (Pi 5 vs Development) and provides appropriate hardware implementations
"""
import os
import platform
from typing import Dict, Any

from .interfaces.camera_interface import CameraInterface
from .interfaces.motor_interface import MotorInterface
from .interfaces.arm_interface import ArmInterface
from .interfaces.camera_servo_interface import CameraServoInterface
from .interfaces.audio_interface import AudioInterface
from .interfaces.display_interface import DisplayInterface

from .real.real_camera import RealCamera
from .real.real_motors import RealMotors
from .real.real_arms import RealArms
from .real.real_camera_servos import RealCameraServos
from .real.real_audio import RealAudio
from .real.real_display import RealDisplay

from .mock.mock_camera import MockCamera
from .mock.mock_motors import MockMotors
from .mock.mock_arms import MockArms
from .mock.mock_camera_servos import MockCameraServos
from .mock.mock_audio import MockAudio
from .mock.mock_display import MockDisplay


class HardwareManager:
    """Main hardware abstraction manager that detects environment and provides appropriate interfaces"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_pi = self.detect_pi_environment()
        self.force_mock = os.environ.get('USE_MOCK_HARDWARE', 'false').lower() == 'true'

        self._initialize_hardware()

    def detect_pi_environment(self) -> bool:
        """Detect if we're running on a Raspberry Pi 5"""
        try:
            # Check for GPIO memory device
            if not os.path.exists('/dev/gpiomem'):
                return False

            # Check CPU info for BCM2835 (Pi hardware)
            with open('/proc/cpuinfo', 'r') as f:
                cpu_info = f.read()
                if 'bcm2835' not in cpu_info.lower():
                    return False

            # Check for Pi 5 specific hardware
            if os.path.exists('/proc/device-tree/model'):
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read()
                    if 'raspberry pi 5' in model.lower():
                        return True

            return True
        except Exception:
            return False

    def _initialize_hardware(self):
        """Initialize hardware interfaces based on detected environment"""
        use_real_hardware = self.is_pi and not self.force_mock

        # Camera Interface
        self.camera: CameraInterface = (
            RealCamera(self.config.get('camera', {})) if use_real_hardware
            else MockCamera(self.config.get('camera', {}))
        )

        # Motor Interface (L298N dual motor driver)
        self.motors: MotorInterface = (
            RealMotors(self.config.get('motors', {})) if use_real_hardware
            else MockMotors(self.config.get('motors', {}))
        )

        # Arm Interface (2 arms × 4 servos each)
        self.arms: ArmInterface = (
            RealArms(self.config.get('arms', {})) if use_real_hardware
            else MockArms(self.config.get('arms', {}))
        )

        # Camera Servo Interface (pan/tilt for camera)
        self.camera_servos: CameraServoInterface = (
            RealCameraServos(self.config.get('camera_servos', {})) if use_real_hardware
            else MockCameraServos(self.config.get('camera_servos', {}))
        )

        # Audio Interface (speaker + microphone)
        self.audio: AudioInterface = (
            RealAudio(self.config.get('audio', {})) if use_real_hardware
            else MockAudio(self.config.get('audio', {}))
        )

        # Display Interface (emotion display)
        self.display: DisplayInterface = (
            RealDisplay(self.config.get('display', {})) if use_real_hardware
            else MockDisplay(self.config.get('display', {}))
        )

    def get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        return {
            'is_pi': self.is_pi,
            'force_mock': self.force_mock,
            'platform': platform.system(),
            'architecture': platform.machine(),
            'using_real_hardware': self.is_pi and not self.force_mock,
            'hardware_status': {
                'camera': self.camera.is_connected(),
                'motors': self.motors.is_connected(),
                'arms': self.arms.is_connected(),
                'camera_servos': self.camera_servos.is_connected(),
                'audio': self.audio.is_connected(),
                'display': self.display.is_connected()
            }
        }

    def emergency_stop(self):
        """Emergency stop all hardware"""
        try:
            self.motors.emergency_stop()
            self.arms.emergency_stop()
            self.camera_servos.stop()
            print("Emergency stop executed successfully")
        except Exception as e:
            print(f"Error during emergency stop: {e}")

    def shutdown(self):
        """Graceful shutdown of all hardware"""
        try:
            self.camera.shutdown()
            self.motors.shutdown()
            self.arms.shutdown()
            self.camera_servos.shutdown()
            self.audio.shutdown()
            self.display.shutdown()
            print("Hardware manager shutdown completed")
        except Exception as e:
            print(f"Error during shutdown: {e}")